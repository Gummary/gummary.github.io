---
title: "Dubbo中的负载均衡策略（下）"
slug: dubbo负载均衡下
date: 2021-10-08T16:06:24+08:00
draft: false
categories: ["Dubbo"]
---

<!--more-->

# 引言

{{< tfigure src="images/2021-09-09-20-53-52.png" title="Dubbo架构图" width="" class="align-center">}}

Dubbo负载均衡是在Dubbo框架的第5层（自上而下）Cluster层，客户端根据注册中心提供的服务端列表，根据配置的负载均衡算法选择一个最佳的调用者。Dubbo提供的负载均衡算法列表如下：

- RandomLoadBalance，加权随机负载均衡
- RoundRobinLoadBalance，加权轮询负载均衡
- LeastActiveLoadBalance，最少连接数
- ShortestResponseLoadBalance，最短响应时间
- ConsistentHashLoadBalance，一致性 Hash

在中篇中介绍了最少连接数和最短时间响应两种负载均衡算法，在本篇中介绍Dubbo中最后一种负载均衡算法——一致性Hash算法。我们首先介绍下最基础的Hash算法及其存在的问题，然后介绍一致性哈希算法是如何缓解这个问题的，最后介绍一致性哈希负载均衡在Dubbo中的实现。

# 哈希算法

假设我们现在有3台服务器，我们希望将来源ip地址相同的请求都分配到同一个Provider上。最简单的实现方式是，对来源ip进行hash，使用hash值对节点数量取余，然后用余数选择服务器。伪代码为：

```python
servers = ['A', 'B', 'C']
def hash_select(source_ip: str):
	idx = hash(source_ip) % len(servers)
	return servers[idx]
```

如果服务器的数量不发生变化，那么这种算法可以保证相同来源ip的流量被准确转发到同一个机器上。但是，如果一个服务器挂了或者新增一个服务器节点，就会使原来的哈希值失效。我们以增加一台服务器为例，此时hash的过程从`hash(ip) % 3`变为`hash(ip) % 4`，假设之前选择2号服务器，也即取余结果为2，则hash值为`n=3t+2`，那么新的hash值为`(3t+2) % 4 = [3(t%4)+2]%4`，其结果可能为0，1，2，3。所以有75%的概率不能分配到原来的服务器中。如果用户的缓存都存在原服务器上，为了防止出现缓存失效导致的缓存雪崩等问题，就需要对这些用户信息进行转移，极大的增加了扩容成本。

# 一致性哈希算法

## 一致哈希算法原理

一致性哈希算法可以很好的解决服务器变动带来的哈希值变化的问题。一致性哈希的核心数据结构是一个哈希环，哈希环由$2^{32}$个节点组成，结构如下图所示：

{{< tfigure src="images/hash-ring.jpg" title="哈希环结构" width="30%" class="align-center">}}

一致性哈希算法首先对服务器地址进行hash，将hash值映射到$[0, 2^{32}-1]$内，假设此时哈希环如下：

{{< tfigure src="images/hash-ring-server.jpg" title="哈希环结构" width="40%" class="align-center">}}

当有新的请求时，同样将请求地址进行hash，将hash值映射到$[0, 2^{32}-1]$内，然后顺时针寻找服务器节点，找到的第一个节点作为本次请求的服务节点，如下图所示，此次请求将选择服务器C。

{{< tfigure src="images/hash-ring-request.jpg" title="哈希环结构" width="40%" class="align-center">}}

下面看下当服务器进行缩容/扩容时的情况。当服务器数量减少时，假设服务器B挂了，那么只有服务器B的流量会重新进行分配，而A和C原来的流量都不需要重新分配；而当有新的节点增加时，假设新服务器D的哈希值在A和C之间，那么只有服务器C的一部分流量会重新分配到D上，A和B的流量都不受影响。

{{< tfigure src="images/hash-server-rm-add.jpg" title="删除/新增节点" width="70%" class="align-center">}}

通过哈希环，一致性哈希算法一定程度上解决了服务器缩容扩容带来的问题。但是如果每个服务器在哈希环上只有一个节点，那么当B服务挂掉后，B的流量全都打到A上了，如果A的承载能力远小于B，那么此时可能直接把A打挂；而如果因为流量太大想进行扩容，新增服务器D之后，D只分担了服务器C的流量，A、B的流量仍不变。所以我们需要一致性哈希算法能够在节点宕机时，将该节点的流量均匀分配到其他节点；在新增节点时，每个节点的一部分流量都能打到新节点上。

为了实现上述的需求，我们可以为每个服务器在哈希环上分配多个虚拟节点，让不同服务器的节点均匀分布在哈希环上，如下图所示：

{{< tfigure src="images/hash-ring-virtual-node.jpg" title="虚拟节点" width="50%" class="align-center">}}

在使用虚拟节点之后，首先根据请求来源找到最近的虚拟节点，然后再根据虚拟节点找到对应的服务器节点。

## 一致性哈希算法-Dubbo实现

下面看下Duboo中如何使用一致性哈希算法实现负载均衡。首先看下负载均衡的过程，dubbo中一致性哈希的粒度是方法级的，当某个方法的invoker数量发生变化时会构造一个新的哈希环，然后在哈希环上选择最近的节点。

```java
protected <T> Invoker<T> doSelect(List<Invoker<T>> invokers, URL url, Invocation invocation) {
	String methodName = RpcUtils.getMethodName(invocation);
	// 负载均衡的粒度是方法级的
	String key = invokers.get(0).getUrl().getServiceKey() + "." + methodName;
	// 计算invoker列表的Hashcode，当list内的元素发生变化时，该值也会发生改变
	int invokersHashCode = invokers.hashCode();
	ConsistentHashSelector<T> selector = (ConsistentHashSelector<T>) selectors.get(key);
	// 当不存在或invoker的列表发生变化时，构造一个新的哈希环
	if (selector == null || selector.identityHashCode != invokersHashCode) {
		selectors.put(key, new ConsistentHashSelector<T>(invokers, methodName, invokersHashCode));
		selector = (ConsistentHashSelector<T>) selectors.get(key);
	}
	// 在哈希环上选择最近的节点
	return selector.select(invocation);
}
```

Dubbo中哈希环是基于Java中的TreeMap实现的，利用TreeMap的排序特性快速找到对应的invoker。哈希环的构造过程在构造函数中实现，使用每个invoker的url地址作为key计算在其在哈希环中的位置；默认情况下每个invoker包含160个虚拟节点。

```java
ConsistentHashSelector(List<Invoker<T>> invokers, String methodName, int identityHashCode) {
	// Hash环
	this.virtualInvokers = new TreeMap<Long, Invoker<T>>();
	this.identityHashCode = identityHashCode;
	URL url = invokers.get(0).getUrl();
	// 获取每个invoker的虚拟节点数量
	this.replicaNumber = url.getMethodParameter(methodName, HASH_NODES, 160);
	// 对于调用方，dubbo使用参数值决定将请求发往哪个节点，这里是判断使用哪些参数。默认情况下使用第一个参数
	String[] index = COMMA_SPLIT_PATTERN.split(url.getMethodParameter(methodName, HASH_ARGUMENTS, "0"));
	argumentIndex = new int[index.length];
	for (int i = 0; i < index.length; i++) {
		argumentIndex[i] = Integer.parseInt(index[i]);
	}
	// 遍历invoker，将invoker加入到哈希环中
	for (Invoker<T> invoker : invokers) {
		String address = invoker.getUrl().getAddress();
		for (int i = 0; i < replicaNumber / 4; i++) {
			byte[] digest = Bytes.getMD5(address + i);
			for (int h = 0; h < 4; h++) {
				long m = hash(digest, h);
				virtualInvokers.put(m, invoker);
			}
		}
	}
}
```

当有新请求时，首先根据调用参数计算出一个哈希值，然后找到第一个比该值大的invoker，如果没有则使用第一个invoker。

```java
public Invoker<T> select(Invocation invocation) {
	// 根据参数值计算哈希值
	String key = toKey(invocation.getArguments());
	byte[] digest = Bytes.getMD5(key);
	// 根据哈希值得到合适的invoekr并返回
	return selectForKey(hash(digest, 0));
}

private String toKey(Object[] args) {
	// 将选择计算哈希值的参数合并到一起，用于计算哈希值
	StringBuilder buf = new StringBuilder();
	for (int i : argumentIndex) {
		if (i >= 0 && i < args.length) {
			buf.append(args[i]);
		}
	}
	return buf.toString();
}

private Invoker<T> selectForKey(long hash) {
	// 找到第一个比该哈希值大的invoker
	Map.Entry<Long, Invoker<T>> entry = virtualInvokers.ceilingEntry(hash);
	// 如果没找到，则使用第一个
	if (entry == null) {
		entry = virtualInvokers.firstEntry();
	}
	return entry.getValue();
}
```

# 总结

本文首先介绍了使用哈希算法如何保证同一个来源的请求都打到同一个服务器上，但是简单的哈希算法在服务器数量变动时会出现哈希失效的问题。而一致性哈希算法利用哈希环在一定程度上缓解了这个问题，减少哈希值变动造成的影响。最后介绍了Dubbo中如何基于Treemap实现一致性哈希算法。

# 参考

1. [Consistent Hashing: Algorithmic Tradeoffs | by Damian Gryski | Medium](https://dgryski.medium.com/consistent-hashing-algorithmic-tradeoffs-ef6b8e2fcae8)
2. [一致性Hash(Consistent Hashing)原理剖析及Java实现](https://blog.csdn.net/suifeng629/article/details/81567777)
3. [Dubbo 一致性Hash负载均衡实现剖析 | Apache Dubbo](https://dubbo.apache.org/zh/blog/2019/05/01/dubbo-%E4%B8%80%E8%87%B4%E6%80%A7hash%E8%B4%9F%E8%BD%BD%E5%9D%87%E8%A1%A1%E5%AE%9E%E7%8E%B0%E5%89%96%E6%9E%90/)
4. [Dubbo一致性哈希负载均衡的源码和Bug，了解一下？](https://segmentfault.com/a/1190000021234695)