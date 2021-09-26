---
title: "Dubbo中的负载均衡策略（中）"
slug: dubbo负载均衡中
date: 2021-09-24T18:17:49+08:00
draft: true
---

<!--more-->

# 引言

{{< tfigure src="images/2021-09-09-20-53-52.png" title="Dubbo架构图" width="" class="align-center">}}

Dubbo负载均衡是在Dubbo框架的第5层（自上而下）Cluster层，客户端根据注册中心提供的服务端列表，根据配置的负载均衡算法选择一个最佳的调用者。Dubbo提供的负载均衡算法列表如下：

- RandomLoadBalance，加权随机负载均衡
- RoundRobinLoadBalance，加权轮询负载均衡
- LeastActiveLoadBalance，最少活跃调用数
- ShortestResponseLoadBalance，最短响应时间
- ConsistentHashLoadBalance，一致性 Hash

在上篇中介绍了加权随机负载均衡与加权轮询负载均衡算法，在本篇中将介绍最短响应时间和最少活跃调用数这两种负载均衡算法。

# 统计RPC调用性能

对于最短响应时间和最少活跃调用数这两种负载均衡算法都需要统计RPC调用状态，最短响应时间需要求出每个Provider的平均响应时间，最少活跃调用数需要统计每个Provider的调用请求。这两个指标都是利用RPCStatus这个类提供的方法进行统计的，所以这里先介绍下RPCStatus这个类。

RpcStatus是一个线程安全的类，可以提供Service/Method粒度的Rpc调用统计信息。先看下RpcStatus的主要成员变量。

```java
public class RpcStatus {
	// Service级别的统计信息
    private static final ConcurrentMap<String, RpcStatus> SERVICE_STATISTICS = new ConcurrentHashMap<String,
            RpcStatus>();
	// Method级别的统计信息
    private static final ConcurrentMap<String, ConcurrentMap<String, RpcStatus>> METHOD_STATISTICS =
            new ConcurrentHashMap<String, ConcurrentMap<String, RpcStatus>>();
	// 其他信息
    private final ConcurrentMap<String, Object> values = new ConcurrentHashMap<String, Object>();

	// 记录当前活跃的链接数量
    private final AtomicInteger active = new AtomicInteger();
	// 记录请求的总数量
    private final AtomicLong total = new AtomicLong();
	// 记录失败请求的总数量
    private final AtomicInteger failed = new AtomicInteger();
	// 记录请求的总响应时间
    private final AtomicLong totalElapsed = new AtomicLong();
	// 记录失败请求的总响应时间
    private final AtomicLong failedElapsed = new AtomicLong();
	// 记录最长的请求响应时间 = max(failed, succeeded)
    private final AtomicLong maxElapsed = new AtomicLong();
	// 记录最长的失败请求响应时间
    private final AtomicLong failedMaxElapsed = new AtomicLong();
	// 记录最长的成功请求响应时间
    private final AtomicLong succeededMaxElapsed = new AtomicLong();
}
```

RpcStatus提供了两个方法beginCount和endCount两个方法，在每次进行Rpc调用之前调用beginCount，Rpc调用结束之后调用endCount即可完成对这次Rpc调用的统计，所以通常会将这两个方法的调用放在某个Filter中执行。

先来看下beginCount方法：

```java
public static boolean beginCount(URL url, String methodName, int max) {
	max = (max <= 0) ? Integer.MAX_VALUE : max;
	// 获取Service粒度的RpcStatus
	RpcStatus appStatus = getStatus(url);
	// 获取Method粒度的RpcStatus
	RpcStatus methodStatus = getStatus(url, methodName);

	if (methodStatus.active.get() == Integer.MAX_VALUE) {
		return false;
	}
	// CAS方式更新method粒度的active数量，原因见https://github.com/apache/dubbo/pull/5881
	for (int i; ; ) {
		i = methodStatus.active.get();

		if (i == Integer.MAX_VALUE || i + 1 > max) {
			return false;
		}

		if (methodStatus.active.compareAndSet(i, i + 1)) {
			break;
		}
	}
	// 因为同一Service的调用次数<= Method的调用次数，所以这里不需要判断是否超过最大值
	appStatus.active.incrementAndGet();

	return true;
}
```

# 最短响应时间负载均衡算法



