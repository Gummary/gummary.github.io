---
title: "Dubbo中的负载均衡策略（中）"
slug: dubbo负载均衡中
date: 2021-09-24T18:17:49+08:00
draft: false
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

在上篇中介绍了加权随机负载均衡与加权轮询负载均衡算法，在本篇中主要介绍最短响应时间和最少活跃调用数这两种负载均衡算法，另外简单介绍Dubbo扩展提供的PeakEwma算法。

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

	// 记录当前活跃的连接数量
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

先来看下beginCount方法，在beginCount方法中，只更新活跃的连接数量。

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
	// 更新service粒度的active数量
	appStatus.active.incrementAndGet();
	return true;
}
```

再来看下endCount方法，在endCount方法中，同时更新了请求数量、时间和活跃连接数等信息。

```java
public static void endCount(URL url, String methodName, long elapsed, boolean succeeded) {
	// 更新Service粒度的Status
	endCount(getStatus(url), elapsed, succeeded);
	// 更新Method粒度的Status
	endCount(getStatus(url, methodName), elapsed, succeeded);
}

private static void endCount(RpcStatus status, long elapsed, boolean succeeded) {
	// 是否成功及请求响应时间都是由调用者传入的
	status.active.decrementAndGet();
	status.total.incrementAndGet();
	status.totalElapsed.addAndGet(elapsed);
	if (status.maxElapsed.get() < elapsed) {
		status.maxElapsed.set(elapsed);
	}
	if (succeeded) {
		if (status.succeededMaxElapsed.get() < elapsed) {
			status.succeededMaxElapsed.set(elapsed);
		}
	} else {
		status.failed.incrementAndGet();
		status.failedElapsed.addAndGet(elapsed);
		if (status.failedMaxElapsed.get() < elapsed) {
			status.failedMaxElapsed.set(elapsed);
		}
	}
}
```

# 最小连接数负载均衡算法

在有了RpcStatus这个统计工具类之后，我们来看下如何计算一个Service的最短响应时间。先从简单的最小连接数开始，最小连接数负载均衡算法主要利用了RpcStatus中的active变量，在负载均衡时选择该值最小的一个Provider。

```java
protected <T> Invoker<T> doSelect(List<Invoker<T>> invokers, URL url, Invocation invocation) {
	// ... 省略变量定义

	// 遍历invoker，找到连接数最小的Provider
	for (int i = 0; i < length; i++) {
		Invoker<T> invoker = invokers.get(i);
		// 获取Invoker的活跃请求数量
		int active = RpcStatus.getStatus(invoker.getUrl(), invocation.getMethodName()).getActive();
		// 获取默认权重
		int afterWarmup = getWeight(invoker, invocation);
		// save for later use
		weights[i] = afterWarmup;
		// 比较得到最小连接数的Provider
		if (leastActive == -1 || active < leastActive) {
			leastActive = active;
			leastCount = 1;
			leastIndexes[0] = i;
			totalWeight = afterWarmup;
			firstWeight = afterWarmup;
			sameWeight = true;
		} else if (active == leastActive) {
			leastIndexes[leastCount++] = i;
			totalWeight += afterWarmup;
			if (sameWeight && afterWarmup != firstWeight) {
				sameWeight = false;
			}
		}
	}
	// 连接数相同根据权重随机选，权重相同直接随机选择
	if (leastCount == 1) {
		return invokers.get(leastIndexes[0]);
	}
	if (!sameWeight && totalWeight > 0) {
		int offsetWeight = ThreadLocalRandom.current().nextInt(totalWeight);
		for (int i = 0; i < leastCount; i++) {
			int leastIndex = leastIndexes[i];
			offsetWeight -= weights[leastIndex];
			if (offsetWeight < 0) {
				return invokers.get(leastIndex);
			}
		}
	}
	return invokers.get(leastIndexes[ThreadLocalRandom.current().nextInt(leastCount)]);
}
```

这种处理方式有个问题是，如果不同的Service的处理能力不同，那么整个cluster的性能最终都被限制在处理能力最小的那个机器上了。

# 最短响应时间负载均衡算法

最短响应时间负载均衡算法可以根据Provider的处理能力进行流量分配。先说下基本原理，ShortestResponseLoadBalance是先统计一段时间窗口内响应时间的平均值，然后计算该Provider的平均响应时间与当前连接数量的乘积作为最短响应时间。使用乘积的方式可以在负载均衡的时候同时考虑连接数+响应时间，让性能更优的服务器处理更多的响应。而只统计一段时间窗口内的平均响应时间是因为，当Provider长时间运行时，平均的响应时间不会受短时间内网络波动的影响。

我们来看下时间窗口的结构体：

```java
protected static class SlideWindowData {
	// 定时更新统计数据的线程池
	private final static ExecutorService EXECUTOR_SERVICE = Executors.newSingleThreadExecutor((new NamedThreadFactory("Dubbo-slidePeriod-reset")));

	private long succeededOffset;
	private long succeededElapsedOffset;
	private RpcStatus rpcStatus;

	public SlideWindowData(RpcStatus rpcStatus) {
		this.rpcStatus = rpcStatus;
		this.succeededOffset = 0;
		this.succeededElapsedOffset = 0;
	}

	// 更新时间窗口的值
	public void reset() {
		this.succeededOffset = rpcStatus.getSucceeded();
		this.succeededElapsedOffset = rpcStatus.getSucceededElapsed();
	}

	// 该Provider的平均响应时间
	private long getSucceededAverageElapsed() {
		// 获取成功的请求数量
		long succeed = this.rpcStatus.getSucceeded() - this.succeededOffset;
		if (succeed == 0) {
			return 0;
		}
		// 平均响应时间
		return (this.rpcStatus.getSucceededElapsed() - this.succeededElapsedOffset) / succeed;
	}

	public long getEstimateResponse() {
		// 活跃数 * 平均响应时间
		int active = this.rpcStatus.getActive() + 1;
		return getSucceededAverageElapsed() * active;
	}
}
```

基于该时间窗口实现的平均响应时间最短算法为：

```java
@Override
protected <T> Invoker<T> doSelect(List<Invoker<T>> invokers, URL url, Invocation invocation) {

	// 省略变量定义...

	// 选出响应时间最短的invoker
	for (int i = 0; i < length; i++) {
		Invoker<T> invoker = invokers.get(i);
		RpcStatus rpcStatus = RpcStatus.getStatus(invoker.getUrl(), invocation.getMethodName());
		SlideWindowData slideWindowData = methodMap.computeIfAbsent(rpcStatus, SlideWindowData::new);

		// 计算当前的估计的响应时间
		long estimateResponse = slideWindowData.getEstimateResponse();
		int afterWarmup = getWeight(invoker, invocation);
		weights[i] = afterWarmup;
		// Same as LeastActiveLoadBalance
		if (estimateResponse < shortestResponse) {
			shortestResponse = estimateResponse;
			shortestCount = 1;
			shortestIndexes[0] = i;
			totalWeight = afterWarmup;
			firstWeight = afterWarmup;
			sameWeight = true;
		} else if (estimateResponse == shortestResponse) {
			shortestIndexes[shortestCount++] = i;
			totalWeight += afterWarmup;
			if (sameWeight && i > 0
				&& afterWarmup != firstWeight) {
				sameWeight = false;
			}
		}
	}

	// 更新时间窗口
	if (System.currentTimeMillis() - lastUpdateTime > SLIDE_PERIOD
		&& onResetSlideWindow.compareAndSet(false, true)) {
		//reset slideWindowData in async way
		SlideWindowData.EXECUTOR_SERVICE.execute(() -> {
			methodMap.values().forEach(SlideWindowData::reset);
			lastUpdateTime = System.currentTimeMillis();
			onResetSlideWindow.set(false);
		});
	}

	// response相同根据权重随机选，权重相同直接随机选择
	if (shortestCount == 1) {
		return invokers.get(shortestIndexes[0]);
	}
	if (!sameWeight && totalWeight > 0) {
		int offsetWeight = ThreadLocalRandom.current().nextInt(totalWeight);
		for (int i = 0; i < shortestCount; i++) {
			int shortestIndex = shortestIndexes[i];
			offsetWeight -= weights[shortestIndex];
			if (offsetWeight < 0) {
				return invokers.get(shortestIndex);
			}
		}
	}
	return invokers.get(shortestIndexes[ThreadLocalRandom.current().nextInt(shortestCount)]);
}
```

该负载均衡算法解决了最小连接数负载均衡算法中无法根据服务器能力分配流量的问题，但是由于使用平均响应时间，所以该负载均衡算法对一些延迟比较大的响应并不敏感。


# 扩展：PeakEwmaLoadBalance

PeakEwma也是一种利用响应时间进行负载均衡的算法。与最短响应时间中使用平均响应时间作为权重不同的是，PeakEwma使用Peak Exponential Weighted Moving Averagea，数移动加权平均代替平均响应时间。与直接平均相比，PEwma对网络波动更为敏感。在计算负载均衡的权重时，最近几次响应时间比历史的响应时间拥有更高的权重。

PeakEwma的计算公式如下:

$$
\begin{aligned}
	V_t &= w \times V_{t-1} + (1-w) \times R_t \\\\
	w &= \frac{1}{e^{k*\Delta_t}}
\end{aligned}
$$

其中，$V_t$为当前节点的PEwma值，用于负载均衡的权重，$V_{t-1}$为历史PEwma值，$R_t$为当前的响应时间，w用于平衡当前响应时间与历史响应时间的关系，$\Delta_t$为两次请求之间的间隔时间。从公式可以看出，两次间隔时间越长，w越小，最近的响应时间的权重越大。

PeakEwmaLoadBalance在Dubbo中是以扩展的形式提供的，代码位于[PeakEwmaLoadBalance](https://github.com/apache/dubbo-spi-extensions/blob/master/dubbo-cluster-extensions/dubbo-cluster-loadbalance-peakewma/src/main/java/org/apache/dubbo/rpc/cluster/loadbalance/PeakEwmaLoadBalance.java)

该负载均衡算法实现相对比较简单，限于篇幅这里不再展开。

# 总结

本文对Dubbo框架中提供的最少连接数和最小响应时间及PEwma算法做了分析，其中最少连接数算法适用于Provider性能相近的场景，最小响应时间算法可以根据Provider端实时响应情况进行流量分配，而PEwma算法对网络波动比最小响应时间算法更为敏感。

# 参考

1. https://blog.51cto.com/u_15175878/3513414
2. https://blog.cloudflare.com/i-wanna-go-fast-load-balancing-dynamic-steering/
3. https://github.com/apache/dubbo-spi-extensions
4. https://dubbo.apache.org/zh/docs/v2.7/dev/source/loadbalance/