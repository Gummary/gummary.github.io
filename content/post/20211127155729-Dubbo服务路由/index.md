---
title: "Dubbo服务路由"
slug: Dubbo服务路由
date: 2021-11-27T15:57:29+08:00
draft: false
---

<!--more-->

在[Dubbo服务目录](/post/dubbo服务目录/)中介绍了当Dubbo客户端如何从注册中心获取到可用的Provider，在这之后Dubbo会使用服务路由对这些Provider进行筛选，得到符合配置条件的Provider地址。本文将介绍Dubbo服务路由的使用及实现原理。

# Dubbo服务路由简介

Dubbo中主要是用的有两种路由规则，条件路由和标签路由。条件路由是通过规则匹配的方式是实现Provider筛选，支持Provider服务或Consumer应用两种粒度；标签路由是只能以Provider粒度匹配。

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

标签路由的配置方式类似这里不再赘述。

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

其中Router是接口，定义了路由相关的行为；AbstractRouter是框架（Effective Java Item20）；ListenableRouter是AbstractRouter的实现，同时实现了ConfigurationListener接口，监听配置的变更；AppRouter和ServiceRouter则是ListenableRouter的模板子类，定义了自己的优先级和名称。

对于一个路由规则，从整体上可以分成两部分：conditions和其他。其中conditions下的内容是详细规则，作为ConditionRouter存储在ListenableRouter中；而其他配置则作为原始规则存储在ListenableRouter中。创建一个条件路由规则（以service为例）的整体流程如下图所示：

{{< tfigure src="images/创建service路由.png" title="" width="" class="align-center">}}

而具体规则的解析和匹配都在ConditionRouter中。

## ConditionRouter

ConditionRouter有两种初始化方式，分别是直接根据URL初始化和根据具体的路由规则进行初始化，二者之间的区别就是获取配置的方式不同。不管使用哪种初始化方式，在得到具体的规则之后，都是调同一个init方法解析规则。

我们知道一个路由规则包含两部分，分别是Consumer的匹配器和Provider的过滤器，二者用`=>`隔开。所以在解析规则时，首先利用`=>`将规则切割，然后分别解析匹配器和过滤器，存放到when和then中。

```java
public void init(String rule) {
	try {
		if (rule == null || rule.trim().length() == 0) {
			throw new IllegalArgumentException("Illegal route rule!");
		}
		rule = rule.replace("consumer.", "").replace("provider.", "");
		int i = rule.indexOf("=>");
		String whenRule = i < 0 ? null : rule.substring(0, i).trim();
		String thenRule = i < 0 ? rule.trim() : rule.substring(i + 2).trim();
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

匹配器和过滤器的解析规则相同，所以二者调用同一个parseRule方法。对于一条规则，Dubbo将其看作是由`符号+字母`的组合形式，由符号来控制字母代表的语义：

- 符号部分为空，说明是一个规则的开始，直接创建MatchPair
- 符号为`&`，说明上一个规则已经结束，创建一个新的MatchPair，content为规则的key
- 符号为`=`，说明是规则的值，将其放入当前的MatchPair中；
- 符号为`!=`，同`=`，只是放到mismatch中
- 符号为`,`，说明一个规则中有多个项，也加入到当前的MatchPair中

```java
// ...
String separator = matcher.group(1);
String content = matcher.group(2);
if (StringUtils.isEmpty(separator)) {
	pair = new MatchPair();
	condition.put(content, pair);
}
else if ("&".equals(separator)) {
	if (condition.get(content) == null) {
		pair = new MatchPair();
		condition.put(content, pair);
	} else {
		pair = condition.get(content);
	}
}
// ...
```

构造完规则后，在获取可用的Provider时就会利用这些规则进行匹配，下面我们看下进行匹配的部分。

// TODO 流程图

RouterChain -> ListenableRouter -> ConditionRouter

在ConditionRouter中，首先判断当前规则是否适用于当前调用方，也即现匹配when，如果匹配，则使用then规则过滤当前的Provider url；如果不匹配，则直接返回。

匹配when和then规则的过程稍有不同：

```java
boolean matchWhen(URL url, Invocation invocation) {
	return CollectionUtils.isEmptyMap(whenCondition) || matchCondition(whenCondition, url, null, invocation);
}
private boolean matchThen(URL url, URL param) {
	return CollectionUtils.isNotEmptyMap(thenCondition) && matchCondition(thenCondition, url, param, null);
}
```

when规则的匹配条件是，whenCondition为空或匹配成功；而then规则的匹配方式是当前then规则不为空且匹配成功。也即，如果when规则为空，则表示适用于任意的调用方；而如果then规则为空，则表示禁用所有的Provider。

二者的入参也不同，matchWhen的入参是consumer的地址和invocation，而mathThen的参数是invoker的地址和consumer的地址。

下面看下二者的共同使用的方式`matchCondition`。在matchCondition中，循环遍历该规则下的所有条件规则，根据匹配规则的key，获取每个规则的匹配内容，然后获取对应的值，判断规则和实际值是否相同。

在matchCondition中，共有以下几种匹配方式：

1. 参数匹配，根据调用参数判断是否匹配
2. 根据调用方法名决定是否匹配
3. 根据address（host+port）
4. 根据host
5. 根据url上的参数

根据参数匹配是，判断规则中指定的指和实际调用的参数是否相同，所以比其他的多了提取参数的部分。最终，这些方式都是调用MatchPair的isMatch方法。MatchPair中matches保存的是匹配的值；mismatches中保存的是不匹配的值。

在isMatch中有三种情况：
1. matches不为空，mismatches不为空
2. mismatches不为空，matches不为空
3. matches与mismatches同时不为空

三者的区别在于，优先级不同。最终都是使用UrlUtils的isMatchGlobPattern方法进行匹配。对于使用了参数的情况，先从参数中取出值，然后再进行匹配。

```java
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

# 参考文献

1. https://dubbo.apache.org/zh/docsv2.7/dev/source/router/