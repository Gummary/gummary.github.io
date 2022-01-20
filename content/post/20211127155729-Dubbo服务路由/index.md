---
title: "Dubbo中的服务路由"
slug: Dubbo服务路由
date: 2021-11-27T15:57:29+08:00
draft: false
---

<!--more-->

在[Dubbo服务目录](/post/dubbo服务目录/)中介绍了当Dubbo客户端如何从注册中心获取到可用的Provider，在这之后Dubbo会使用服务路由对这些Provider进行筛选，得到符合配置条件的Provider地址。本文将介绍Dubbo服务路由的使用及实现原理。

# Dubbo服务路由简介

在Directory从注册中心获取到可用的Invoker之后，会调用`routerChain`进行服务路由，使用服务路由可以实现根据调用方、调用方式不同选择不同的Provider，在此基础上实现读写分离、机房隔离、Set化等等功能。所以我们下面就从RouterChain开始说起，详细Dubbo中路由规则如何使用及如何实现的。

# RouterChain的构造

在Directory中是通过RouterChain类实现对Provider地址的过滤，我们先来看下RouterChain是如何构造的。

```java
private RouterChain(URL url) {
    // ...
    // step1 加载所有的路由扩展
    List<RouterFactory> extensionFactories = url.getOrDefaultApplicationModel().getExtensionLoader(RouterFactory.class)
        .getActivateExtension(url, ROUTER_KEY);
    // step2 构造路由规则，并按照优先级排序
    List<Router> routers = extensionFactories.stream()
        .map(factory -> factory.getRouter(url))
        .sorted(Router::compareTo)
        .collect(Collectors.toList());
    // step3 初始化
    initWithRouters(routers);
    // ... 
}
```

路由规则是以SPI扩展的形式存在于Dubbo中的，在RouterChain的构造函数中完成了对路由规则的加载。在Dubbo的内部配置中配置了7个扩展，但是其中只有service、app、tag、mock、mesh-rule这5个为ActivateExtension。

{{< tfigure src="images/2021-11-27-17-46-03.png" title="" width="" class="align-center">}}

在构造完所有的路由规则后，在route方法中会调用所有的路由规则，得到过滤后的Invoker。

service、app和tag分别是Provider服务粒度的条件路由、Consumer应用粒度的条件路由和标签路由，下面我们重点看下service、app和tag这三种路由规则是如何配置及实现的。

# 路由规则的配置

条件路由和标签路由的配置方式都有两种，一种是在[Dubbo Admin](https://github.com/apache/dubbo-admin)中写入注册中心，另一种是通过硬编码的方式写入。

**使用控制台配置路由规则**

使用Dubbo控制台配置条件路由的方式如下：

在Dubbo控制台主页的`服务治理/条件路由`中可以选择创建一个条件路由规则：

{{< tfigure src="images/2021-11-27-16-22-38.png" title="" width="" class="align-center">}}

然后在路由规则中可以指定Service类或应用名，规则内容的具体含义见[Dubbo 路由规则](https://dubbo.apache.org/zh/docs/advanced/routing-rule/)

{{< tfigure src="images/2021-11-27-16-50-44.png" title="" width="70%" class="align-center">}}

标签路由的配置方式类似，这里不再赘述。

**使用硬编码配置**

使用硬编码配置条件路由的方式是，在服务调用前时，向注册中心写入配置即可：

```java
RegistryFactory registryFactory = ExtensionLoader.getExtensionLoader(RegistryFactory.class).getAdaptiveExtension();
Registry registry = registryFactory.getRegistry(URL.valueOf("zookeeper://127.0.0.1:2181"));
registry.register(URL.valueOf("condition://127.0.0.1/com.foo.BarService?category=routers&dynamic=false&rule=" + URL.encode("host = 10.20.153.10 => host = 10.20.153.11") + "));
```

使用硬编码配置条件路由的方式有以下三种，这三种方式是静态打标，也即打标之后就无法修改了，而且优先级也比控制台配置的标签低。

```
<dubbo:provider tag="tag1"/>
<dubbo:service tag="tag1"/>
java -jar xxx-provider.jar -Ddubbo.provider.tag={the tag you want, may come from OS ENV}
```


# 条件路由源码解析

先来看下与条件路由相关的类图：

{{< tfigure src="images/条件路由类图.png" title="" width="" class="align-center">}}

其中Router是接口，定义了路由相关的行为；AbstractRouter是框架（Effective Java Item20）；ListenableRouter是AbstractRouter的实现，同时实现了ConfigurationListener接口，监听配置的变更；AppRouter和ServiceRouter则是ListenableRouter的模板子类，分别用于应用级和接口级，在子类内部定义了自己的优先级和名称。

对于一个路由规则，从整体上可以分成两部分：conditions和其他。其中conditions下的内容是详细规则，作为ConditionRouter存储在ListenableRouter中；而其他配置则作为原始规则存储在ListenableRouter中。创建一个条件路由规则（以service为例）的整体流程如下图所示：

{{< tfigure src="images/创建service路由.png" title="" width="" class="align-center">}}

具体规则的解析和匹配都在ConditionRouter中。

## ConditionRouter源码解析

我们从初始化开始看起，ConditionRouter有两种初始化方式，分别是直接根据URL初始化和根据具体的路由规则进行初始化。二者之间的区别在于获取规则的方式不同，前者从URL中获取，后者从配置中心获取。但不管使用哪种初始化方式，在得到具体的规则之后，都是调同一个init方法解析规则。

我们知道一个路由规则包含两部分，分别是Consumer的匹配器和Provider的过滤器，二者用`=>`隔开。所以在解析规则时，首先利用`=>`将规则分开，然后分别解析匹配器和过滤器，存放到when和then中。

```java
public void init(String rule) {
    try {
        if (rule == null || rule.trim().length() == 0) {
            throw new IllegalArgumentException("Illegal route rule!");
        }
        // step1 分割规则，得到匹配器和过滤器
        rule = rule.replace("consumer.", "").replace("provider.", "");
        int i = rule.indexOf("=>");
        String whenRule = i < 0 ? null : rule.substring(0, i).trim();
        String thenRule = i < 0 ? rule.trim() : rule.substring(i + 2).trim();
        // step2 解析规则，存放为MatchPair
        Map<String, MatchPair> when = StringUtils.isBlank(whenRule) || "true".equals(whenRule) ? new HashMap<String, MatchPair>() : parseRule(whenRule);
        Map<String, MatchPair> then = StringUtils.isBlank(thenRule) || "false".equals(thenRule) ? null : parseRule(thenRule);
        // NOTE: It should be determined on the business level whether the `When condition` can be empty or not.
        this.whenCondition = when;
        this.thenCondition = then;
    } catch (ParseException e) {
        throw new IllegalStateException(e.getMessage(), e);
    }
}
```

匹配器和过滤器的解析规则相同，所以二者调用同一个parseRule方法。对于一条规则，Dubbo将其看作是由多个`符号+字符串`组合的形式，由符号来控制字符串代表的语义，具体有以下几种：

- 符号部分为空，说明是一个规则的开始，直接创建MatchPair
- 符号为`&`，说明当前规则有多个条件且上一个条件已经解析结束，所以创建一个新的MatchPair，content为新条件的key
- 符号为`=`，说明是内容是规则的值，将其放入当前的MatchPair的match集合中；
- 符号为`!=`，同`=`，只不过将规则的值放到MatchPair的mismatch集合中
- 符号为`,`，说明一个规则中有多个值，所以将解析出的值也加入到当前的MatchPair中

所以在parseRule中，使用正则表达式不断提取`符号+字符串`这一组合，不断解析规则，构造MatchPair。限于篇幅，下面摘出部分解析的代码进行说明：

```java
// ...
// matcher是正则表达式的匹配结果
String separator = matcher.group(1);
String content = matcher.group(2);
// 处理规则的开始
if (StringUtils.isEmpty(separator)) {
    pair = new MatchPair();
    condition.put(content, pair);
}
// 处理多个条件的情况
else if ("&".equals(separator)) {
    // condition是一条规则
    if (condition.get(content) == null) {
        pair = new MatchPair();
        condition.put(content, pair);
    } else {
        pair = condition.get(content);
    }
}
// ...
```

所以规则的解析过程就是将键值对拆开并存下来，在服务路由时利用这些规则进行路由匹配，下面我们就看下进行匹配的部分，核心代码如下：

```java
// step1 首先判断当前Consumer是否匹配当前规则
if (!matchWhen(url, invocation)) {
    return new RouterResult<>(invokers);
}
// step2 如果过滤规则为空，说明禁用当前的调用者，直接返回空列表
List<Invoker<T>> result = new ArrayList<Invoker<T>>();
if (thenCondition == null) {
    logger.warn("The current consumer in the service blacklist. consumer: " + NetUtils.getLocalHost() + ", service: " + url.getServiceKey());
    return new RouterResult<>(result);
}
// step3 遍历所有Invoker，如果符合规则条件则加入到结果中
for (Invoker<T> invoker : invokers) {
    if (matchThen(invoker.getUrl(), url)) {
        result.add(invoker);
    }
}
// step4 返回结果
if (!result.isEmpty()) {
ret urn new RouterResult<>(result);
} else if (this.isForce()) {
    logger.warn("The route result is empty and force execute. consumer: " + NetUtils.getLocalHost() + ", service: " + url.getServiceKey() + ", router: " + url.getParameterAndDecoded(RULE_KEY));
    return new RouterResult<>(result);
}
```

路由过程中的两个核心方法是matchWhen和matchThen，二者的结构类似，但实现方式完全不同：

```java
boolean matchWhen(URL url, Invocation invocation) {
    return CollectionUtils.isEmptyMap(whenCondition) || matchCondition(whenCondition, url, null, invocation);
}
private boolean matchThen(URL url, URL param) {
    return CollectionUtils.isNotEmptyMap(thenCondition) && matchCondition(thenCondition, url, param, null);
}
```

when规则的匹配条件是，whenCondition为空或匹配成功；而then规则的匹配方式是当前then规则不为空且匹配成功。也即，如果when规则为空，则表示适用于任意的调用方；而如果then规则为空，则表示禁用所有的Provider。

二者入参和调用matchCondition的方式也不同，matchWhen的入参是consumer的url和invocation，而mathThen的参数是invoker的url和consumer的url作为param。

下面看下二者的共同使用的方式`matchCondition`。在matchCondition中，循环遍历该规则下的所有键值对，键的不同决定了每个键值对的匹配内容，从传入的param或invocation中获取对应的值，判断匹配规则和实际值是否匹配。在matchCondition中，共有以下几种匹配方式：

1. 参数匹配，根据调用参数判断是否匹配
2. 根据调用方法名决定是否匹配
3. 根据address（host+port）
4. 根据host
5. 根据url上的参数

根据参数匹配是，判断规则中指定的值和实际调用的参数是否相同，所以比其他的多了提取参数的部分。但最终这些方式都是调用MatchPair的isMatch方法。在MatchPair中，有matches和mismatches两个集合，前者保存的是匹配的值，后者保存的是不匹配的值。

在isMatch中有三种情况，三者的优先级不同：
1. 当matches不为空，mismatches为空时，判断matches中的内容与值是否相同
2. 当mismatches不为空，matches不为空，判断mismatches中的内容与值是否相同
3. 当matches与mismatches同时不为空时，优先判断mismatches中的值是否相同

判断规则内容和值是否匹配都是使用了`UrlUtils.isMatchGlobPattern`方法。对于使用了参数的情况（包含$），先从参数中取出值，然后再进行匹配。

```java
public static boolean isMatchGlobPattern(String pattern, String value, URL param) {
    if (param != null && pattern.startsWith("$")) {
        pattern = param.getRawParameter(pattern.substring(1));
    }
    return isMatchGlobPattern(pattern, value);
}

public static boolean isMatchGlobPattern(String pattern, String value) {
    // 通配符直接返回true
    if ("*".equals(pattern)) {
        return true;
    }
    // 匹配内容或对象均为空返回true
    if (StringUtils.isEmpty(pattern) && StringUtils.isEmpty(value)) {
        return true;
    }
    // 匹配内容或对象有一项为空返回true
    if (StringUtils.isEmpty(pattern) || StringUtils.isEmpty(value)) {
        return false;
    }
    // 判断是否使用了通配符的情况
    int i = pattern.lastIndexOf('*');
    // 未使用通配符，全量匹配
    if (i == -1) {
        return value.equals(pattern);
    }
    // "*" 在最后，判断value的起始是否与其相同
    else if (i == pattern.length() - 1) {
        return value.startsWith(pattern.substring(0, i));
    }
    // "*" 在开始，判断value的结束是否相同
    else if (i == 0) {
        return value.endsWith(pattern.substring(i + 1));
    }
    // "*" 在中间，同时判断其实和结束
    else {
        String prefix = pattern.substring(0, i);
        String suffix = pattern.substring(i + 1);
        return value.startsWith(prefix) && value.endsWith(suffix);
    }
}
```

# 标签路由源码解析

标签路由相对简单，标签规则作为一个列表存储在TagStateRouter中，我们重点看下路由的过程。

```java
// ...

BitList<Invoker<T>> result = invokers;
String tag = StringUtils.isEmpty(invocation.getAttachment(TAG_KEY)) ? url.getParameter(TAG_KEY) :
    invocation.getAttachment(TAG_KEY);

// 如果consumer在调用时指定了tag
if (StringUtils.isNotEmpty(tag)) {
    // 获取动态标签规则(配置中心配置)中匹配该tag的所有invoker地址
    List<String> addresses = tagRouterRuleCopy.getTagnameToAddresses().get(tag);
    if (CollectionUtils.isNotEmpty(addresses)) {
        result = filterInvoker(invokers, invoker -> addressMatches(invoker.getUrl(), addresses));
        // if result is not null OR it's null but force=true, return result directly
        if (CollectionUtils.isNotEmpty(result) || tagRouterRuleCopy.isForce()) {
            return new StateRouterResult<>(result,
                needToPrintMessage ? "Use tag " + tag + " to route. Reason: result is not null OR it's null but force=true" : null);
        }
    } else {
        // 从invoker的url参数中获取代码指定的标签，获取所有匹配当前标签的路由
        result = filterInvoker(invokers, invoker -> tag.equals(invoker.getUrl().getParameter(TAG_KEY)));
    }
    // 如果路由结果不为空或强制使用标签路由，则直接返回过滤结果
    if (CollectionUtils.isNotEmpty(result) || isForceUseTag(invocation)) {
        return new StateRouterResult<>(result,
            needToPrintMessage ? "Use tag " + tag + " to route. Reason: result is not empty or ForceUseTag key is true in invocation" : null);
    }
    else {
        // 如果没有找到对应标签的provider，那么返回所有不含标签的provider
        BitList<Invoker<T>> tmp = filterInvoker(invokers, invoker -> addressNotMatches(invoker.getUrl(),
            tagRouterRuleCopy.getAddresses()));
        return new StateRouterResult<>(filterInvoker(tmp, invoker -> StringUtils.isEmpty(invoker.getUrl().getParameter(TAG_KEY))),
            needToPrintMessage ? "FAILOVER: return all Providers without any tags" : null);
    }
} else {
    // 对于调用时不指定标签的情况，将invoker中包含静态标签和动态标签的provider过滤掉
    List<String> addresses = tagRouterRuleCopy.getAddresses();
    if (CollectionUtils.isNotEmpty(addresses)) {
        result = filterInvoker(invokers, invoker -> addressNotMatches(invoker.getUrl(), addresses));
        // 1. all addresses are in dynamic tag group, return empty list.
        if (CollectionUtils.isEmpty(result)) {
            return new StateRouterResult<>(result,
                needToPrintMessage ? "all addresses are in dynamic tag group, return empty list" : null);
        }
        // 2. if there are some addresses that are not in any dynamic tag group, continue to filter using the
        // static tag group.
    }
    return new StateRouterResult<>(filterInvoker(result, invoker -> {
        String localTag = invoker.getUrl().getParameter(TAG_KEY);
        return StringUtils.isEmpty(localTag) || !tagRouterRuleCopy.getTagNames().contains(localTag);
    }), needToPrintMessage ? "filter using the static tag group" : null);
}
```

以上就是标签路由的核心流程，比条件路由容易理解。总体来看就是：

- 如果客户端打标签了，就过滤出所有有该标签的provider；如果没有符合条件的provider，则返回所有无标签的provider
- 如果客户端没打标签，就把所有有静态和动态标签的provider过滤掉，返回剩下的provider

# 总结

以上就是本文的全部内容，先从路由规则的入口RouterChain入手，介绍了路由规则的加载过程，然后介绍了如果配置条件路由和规则路由，其中使用Dubbo控制台的方式更为友好，最后详细分析了条件路由和标签路由的实现原理。

# 参考文献

1. [服务路由 | Apache Dubbo](https://dubbo.apache.org/zh/docsv2.7/dev/source/router/)
2. [路由规则 | Apache Dubbo](https://dubbo.apache.org/zh/docs/v3.0/references/features/routing-rule/)
3. [dubbo源码：dubbo中条件路由配置及原理](https://blog.csdn.net/zhuqiuhui/article/details/90413512#21__10)
4. [GitHub - apache/dubbo-admin: The ops and reference implementation for Apache Dubbo](https://github.com/apache/dubbo-admin)
5. [Dubbo-Router条件路由、脚本路由使用](https://blog.csdn.net/hosaos/article/details/103495881)
6. [6.33 路由规则 · dubbo-user-book](https://dubbo.gitbooks.io/dubbo-user-book/content/demos/routing-rule.html)