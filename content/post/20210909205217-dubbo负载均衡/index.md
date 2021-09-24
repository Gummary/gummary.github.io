---
title: "Dubbo中的负载均衡策略"
slug: Dubbo3负载均衡
date: 2021-09-09T20:52:17+08:00
draft: true
categories: ["Dubbo"]
---

<!--more-->

# 引言

{{< figure src="images/2021-09-09-20-53-52.png" title="Dubbo架构图" width="" class="align-center">}}

Dubbo负载均衡是在Dubbo框架的第5层（自上而下）Cluster层，客户端根据注册中心提供的服务端列表，根据配置的负载均衡算法选择一个最佳的调用者。Dubbo提供的负载均衡算法列表如下：

- RandomLoadBalance，加权随机负载均衡
- RoundRobinLoadBalance，加权轮询负载均衡
- LeastActiveLoadBalance
- ShortestResponseLoadBalance
- ConsistentHashLoadBalance

本文将首先介绍各随机算法的原理，然后结合Dubbo中代码分析具体实现。

# 随机负载均衡

## 负载均衡算法简介

随机负载均衡是从服务器列表中随机选择一个服务器提供服务，当请求量足够大时，各服务器分配到的流量近似相同。这样完全随机有一个问题是，不同服务器的处理能力不同，完全随机不能将处理能力强的服务器的能力全部发挥出来，另外也会对处理能力弱的服务器造成一定压力。所以我们需要根据服务器的处理能力给服务器添加权重，让高权重的服务器处理更多的请求。

在有了各服务器的权重后，如何进行分配呢？这里介绍一种非常巧妙的算法：

假设我们现在有A,B,C三个Provider，权重分别为2,8,1，权重和为11，将invoker根据权重放在坐标轴上有：

{{< figure src="images/2021-09-09-22-03-33.png" title="" width="" class="align-center">}}

然后生成一个大于0小于权重和的随机数，假设生成的随机数为s，若：

- $0\leq s < 2$，则选择服务A；
- $2\leq s < 10$，则选择服务B；
- $10\leq s < 11$，则选择服务C。

这样，权重越大的服务器，生成的随机数命中该服务器权重区域的概率就越大。

## Dubbo中的加权随机负载均衡实现

加权随机负载均衡是Dubbo使用的默认负载均衡算法，用户可指定不同服务器的权重，使用相同的默认权重。RandomLoadBalance的核心代码如下：

```java
protected <T> Invoker<T> doSelect(List<Invoker<T>> invokers, URL url, Invocation invocation) {
	
	// 获得所有invoker的数量
	int length = invokers.size();

	if (!needWeightLoadBalance(invokers,invocation)){
		return invokers.get(ThreadLocalRandom.current().nextInt(length));
	}

	// 用于判断是否所有的invoker都有相同的权重
	boolean sameWeight = true;
	// 存储每个invoker的最大权重，也即累积和
	int[] weights = new int[length];
	// 计算权重和
	int totalWeight = 0;
	for (int i = 0; i < length; i++) {
		// 计算每个invoker的权重
		int weight = getWeight(invokers.get(i), invocation);
		// 求和
		totalWeight += weight;
		// 存储每个invoker当前的累积和
		weights[i] = totalWeight;
		// 判断权重是否不同
		if (sameWeight && totalWeight != weight * (i + 1)) {
			sameWeight = false;
		}
	}
	
	if (totalWeight > 0 && !sameWeight) {
		// 如果各个invoker的权重不相同，则根据我们上一节介绍的算法随机选出一个invoker
		int offset = ThreadLocalRandom.current().nextInt(totalWeight);
		for (int i = 0; i < length; i++) {
			if (offset < weights[i]) {
				return invokers.get(i);
			}
		}
	}
	// 如果权重和为0或权重均相同，则随机返回一个
	return invokers.get(ThreadLocalRandom.current().nextInt(length));
}
```

# 轮询负载均衡

## 完全轮询负载均衡

完全轮询负载均衡算法比较简单，不断遍历服务器列表即可。与随机算法相同，不能根据服务器的能力去分配流量。所以也需要通过权重控制流量分配。

```python
servers = ['A', 'B', 'C']
index = 0
def select():
	global index
	index = (index+1) % len(servers)
	return servers[index]
```

## 加权轮询负载均衡

加权轮询负载均衡与加权随机算法实现方式类似，但是不再生成随机数，而是累计一个值，该值在哪个区间内就请求哪个服务器。

```python
servers = [(2, 'A'), (8, 'B'), (1, 'C')]
index = 0

def select():
	global index
	total_weight = 0
	weights = [0] * len(servers)
	target_server = servers[0]
	for i in range(len(servers)):
		total_weight += servers[i][0]
		weights[i] = total_weight
	for i in range(len(servers)):
		if index < weights[i]:
			target_server = servers[i]
			break
	index = (index + 1) % total_weight
	return target_server
```

这种负载均衡算法也有其缺点，考虑当某个服务器的权重特别大时，那么所有的请求都会发送给该服务器，而其他的服务器则没有流量。

## 平滑加权轮询负载均衡

为了防止出现某个服务器压力过大的情况，Nginx在一次更新中提出一种平滑负载均衡算法，算法原文描述为：

> Algorithm is as follows: on each peer selection we increase current_weight of each eligible peer by its weight, select peer with greatest current_weight and reduce its current_weight by total number of weight points distributed among peers.

假设共有n个节点，每个节点的权重分别为$[x_1, \dots, x_n]$，和为$S$，初始化时将所有节点的当前权重设置为0，在每次负载均衡选择执行两个步骤：

1. 将每个节点的当前权重加上每个节点的权重，选出当前权重最大的节点。
2. 将权重最大的节点的当前权重减去权重和S。

算法的步骤很简单，但是背后的原理却很反直觉，为什么这样平滑了呢？这样就能均衡的访问每个服务器吗？下面给出一个数学证明，对此不感兴趣的读者可直接跳到[Dubbo实现]({{< relref "#dubbo中的平滑加权轮询负载均衡" >}})。

我们先来证明均衡性，也即在选择$S$次后，每个节点选择的次数均为$x_i$。

假设在第$t$轮的时候，第$j$个节点已经选了$x_j$次，其中$x_j \leq t < S$，此时第$j$个节点的权重为:

$$
\begin{aligned}
w_j(t) & = t\times x_j - x_j\times S \\\\ 
&= (t-S)\times x_j \\\\
&< 0
\end{aligned}
$$

而我们在每个loadbalance的过程中，先将每个节点的当前权重加上每个节点的权重，然后最大的减去权重和，总的来看，所有节点的权重和仍然为0.

1. $x_1 + \dots + x_n$，假设最大的为第$j$个
2. $x_1 + \dots + (x_j - S) + \dots + x_n = x_1 + \dots + x_n - S = 0$

所以每次进行选择时当前权重和均为0，又有$w_j(t) < 0$，那么必定存在一个节点的权重满足$w_p(t) > 0$。所以当一个节点被选择$x_j$次之后一定不会再选择该节点。在之后的$S-t$次选择中，随着t的增大$w_j(t)= (t-S)\times x_j$会不断趋向于0，直至$t=S$时，$w_j(t)=0$。

所以，每个节点在被选择$x_i$次之后，都不会再被选择，而我们一共选择S次，所以每个节点都会被恰好选择$x_i$次，满足均衡性。

我们再来证明平滑性。平滑性是指，当$x_i > 1$时，在选择$x_i-1$次某个节点之后，下一次一定不会再选择第i个节点了。

假设在$t$时刻，我们连续选择了$x_i-1$次$i$节点。在这之前，我们选择了$n$次$j$节点且$j$节点仍未被轮询完，也即$0\leq n\leq x_j-1$，则有：

$$
\begin{aligned}	
	w_i(t) &= t\times x_i - (x_i-1)\times S \\\\
	w_j(t) &= t\times x_j - n\times S \\\\
		   &\geq t\times x_j - (x_j-1) \times S	
\end{aligned} \tag {1}
$$

此时分两种情况讨：

**若当前恰好是前$t$个时刻**，则有：

$$
\begin{aligned}
	t &= x_i-1 \\\\
	n &= 0 \\\\
	w_i(t) &= t\times x_i - (x_i-1)\times S \\\\
	w_j(t) &= t\times x_j - n\times S \\\\
		   &\geq t\times x_j - (x_j-1) \times S	
\end{aligned}\tag {2}
$$

在$t+1$时刻有：

$$
\begin{aligned}
	w_i(t) &= (x_i-1)\times x_i - (x_i-1)\times S + x_i \\\\
		   &= (x_i-1)\times(x_i-S) + x_i \\\\
		   &\leq x_i - x_i + 1 \\\\
		   &\leq 1
\end{aligned}\tag {3}
$$

其中第3步中是因为$x_i-S < 0 \Rightarrow x_i - S \leq -1$。其他节点的权重为：

$$
\begin{aligned}
w_j(t) &= (x_i-1)\times x_j + x_j \\\\
		   &= x_i\times x_j
\end{aligned}\tag {4}
$$

所以$w_i(t) < w_j(t)$，在$t+1$时刻一定不会选i节点。

再来看**t不是前t个时刻**:

因为我们在选择i节点之前已经选择过j节点，说明$x_j>x_i$，所以带入到公式$(1)$中就有$w_j(t) > w_i(t)$

## Dubbo中的平滑加权轮询负载均衡实现

# 附录

## Dubbo中计算权重的方式

```java
int getWeight(Invoker<?> invoker, Invocation invocation) {
	int weight;
	URL url = invoker.getUrl();
	// Multiple registry scenario, load balance among multiple registries.
	if (REGISTRY_SERVICE_REFERENCE_PATH.equals(url.getServiceInterface())) {
		weight = url.getParameter(REGISTRY_KEY + "." + WEIGHT_KEY, DEFAULT_WEIGHT);
	} else {
		weight = url.getMethodParameter(invocation.getMethodName(), WEIGHT_KEY, DEFAULT_WEIGHT);
		if (weight > 0) {
			long timestamp = invoker.getUrl().getParameter(TIMESTAMP_KEY, 0L);
			if (timestamp > 0L) {
				long uptime = System.currentTimeMillis() - timestamp;
				if (uptime < 0) {
					return 1;
				}
				int warmup = invoker.getUrl().getParameter(WARMUP_KEY, DEFAULT_WARMUP);
				if (uptime > 0 && uptime < warmup) {
					weight = calculateWarmupWeight((int)uptime, warmup, weight);
				}
			}
		}
	}
	return Math.max(weight, 0);
}
```

# 参考文献

1. http://aibenlin.com/algorithm/2019/07/22/algorithm-weight.html
2. https://tenfy.cn/2018/11/12/smooth-weighted-round-robin/
3. https://hedzr.com/golang/algorithm/go-load-balancer-1/#%E5%B8%A6%E6%9D%83%E9%87%8D%E7%9A%84%E8%BD%AE%E8%AF%A2%E7%AE%97%E6%B3%95-weighted-round-robin
4. https://colobu.com/2016/12/04/smooth-weighted-round-robin-algorithm/