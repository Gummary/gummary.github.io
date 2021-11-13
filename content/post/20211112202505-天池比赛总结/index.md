---
title: "天池比赛总结"
slug: 天池比赛总结
date: 2021-11-12T20:25:05+08:00
draft: false
---

<!--more-->

# 前言

没毕业的时候就和铁铁MTFighting约好，每年肝一次天池中间件比赛，今年比赛一出就报名了，今年本来目标是能进第一页就行，后来工作需求一多就没时间肝了，最后摸了个25名，和第一页差5名，明年继续努力吧Orz

# 赛题

本次赛题是要实现Dubbo的集群柔性调度，集群的柔性调度是指Dubbo能够从全局的角度合理分配请求，达到集群的自适应。具体来说使消费者能够快速地感知服务端节点性能的随机变化，通过调节发送往不同服务端节点的请求数比例分配变得更加合理，让 Dubbo 即使遇到集群大规模部署带来的问题，也可以提供最优的性能。

比赛的环境如下：

{{< tfigure src="images/2021-11-13-11-54-00.png" title="" width="" class="align-center">}}

1. PTS 作为压测请求客户端向 Gateway（Consumer） 发起 HTTP 请求，Gateway（Consumer） 加载用户实现的负载均衡算法选择一个 Provider，Provider 处理请求，返回结果。
2. 每个 Provider 的服务能力 (处理请求的速率) 都会动态变化：
3. 三个 Provider 的每个 Provider 的处理能力会随机变动以模拟超售场景
4. 三个 Provider 任意一个的处理能力都小于总请求量
5. 三个 Provider 的会有一定比例的请求处理超时（5000ms）
6. 三个 Provider 的每个 Provider 会随机离线（本次比赛不依赖 Nacos 的健康检查机制，也即是无地址更新通知）
7. 评测分为预热和正式评测两部分，预热部分不计算成绩，正式评测部分计算成绩。
8. 正式评测阶段，PTS 以固定 RPS 请求数模式向 Gateway 发送请求，1分钟后停止；
9. 以 PTS 统计的成功请求数和最大 TPS 作为排名依据。成功请求数越大，排名越靠前。成功数相同的情况下，按照最大 TPS 排名。


# 解题思路

一开始拿到赛题看到赛题中“三个 Provider 的每个 Provider 会随机离线”，于是就想整一个实时检测是否离线的心跳。做了半天提交之后，发现完全没用，加了大赛的官方群才发现不是关机的这种离线。

然后开始看官方发的赛题分析，这个分析对我们的帮助巨大。视频里提了个三个点：

1. 容量评估，根据服务端性能进行评估处理
2. 快速失败，本次比赛是以总的并发量去进行压测，对于一些超过预期的请求提前结束，提高总的吞吐量
3. 自动探测，对服务容量进行动态分析，达到所有时间的最优解

下面针对这几个点给出我们尝试的的一些有用策略。

## 自动探测

这部分我理解就是做均衡，根据Provider的状态把请求分配到负载最低的节点上。但是这部分我们一直没有好的方法。最开始我们用的随机负载均衡，然后查了资料尝试了PeakEwma算法效果也不是很理想，然后又试了最小连接数，比随机算法高一些，所以就用这个当作Baseline开始容量评估和快速失败的探索。

在探索的过程中，我们发现20890的最大线程数是500，20880和20870的线程数是300，但20880处理请求的能力比20870的是弱一些的。而最小连接数是不care这些的，基本相当于是一个轮询负载均衡，最后每个Provider的并发数都是一样的。所以我们中间做了手动加权处理，给20890分配更多的请求，20880分配少一些请求。

```java
int active = rpcStatus.getActive();
if (port == 20890) {
	active -= 100;
	active = Math.max(0, active);
} else if (port == 20870) {
	active -= 20;
} else {
	active += 20;
}
if (active < minActive) {
	minActive = active;
	minIndex = i;
}
```

由于复赛不提供日志，没办法直接根据端口硬编码，所以改成了将线程池大小作为权重的加权轮训负载均衡，在初赛验证发现效果和最小连接数差不多，就一直沿用到了复赛。

## 快速失败

快速失败在比赛开始是实现最简单，提分最有效的。在代码中将客户端的超时写死成20ms，能直接提高大约200w分。

```java
RpcContext.getClientAttachment().setObjectAttachment(TIMEOUT_KEY, 20);
```

后来赛题改了，设置一个固定超时时间将不再生效，于是我们就开始换成动态探测的方式估计超时时间。为了能快速的根据Provider端处理时间变化而变化，我这里选用了指数加权移动平均（EWMA），但是效果并不好，把估计的超时时间画出来得到的效果如下图所示，估计的处理时间在50-200ms波动，可以说完全没有效果。原因的话，大概是EWMA受最近请求的往返时间影响比较大，如果出现一个Rtt较高的请求，那么之后一段时间估计的值都会在这附近。

{{< tfigure src="images/2021-11-12-21-25-43.png" title="" width="" class="align-center">}}

于是又换成了固定超时时间的方法，这次加上了随机的抖动，防止超时不生效。

```java
double observeRtt = 20.0 + ThreadLocalRandom.current().nextDouble(-2, 2);
RpcContext.getClientAttachment().setObjectAttachment(TIMEOUT_KEY, observeRtt);
```

之后就拿这个当作Baseline去做容量评估了。由于比赛方最后会检测这种随机抖动的情况，所以在初赛的最后一周又回来写估计超时时间的算法。想了一下午没想到合适的解决方案，最后没办法，就硬上TCP估计Rtt的方法，没想到竟然意外的好用，于是就作为最终方案保留到复赛。分析原因的话，TCP估计Rtt的方式和EWMA恰好相反，TCP给之前估计的RTT更多权重，而EWMA给最近的RTT更大权重，所以对于一次比较大的Rtt，我们应该用之前估计的值将其平滑掉。

使用TCP后的图回家补。

## 容量探测

容量探测的部分是做动态估计Rtt做不下去了，Gateway这边整不出花活，所以开始研究Provider了。我这边统计了Provider端的CPU Load、JVM Free Memory、Dubbo线程池中活跃的线程数量，对比了当前的并发量，如下图所示：

![](images/2021-11-12-21-50-34.png)

可以看到，只有活跃线程数和当前并发数的趋势是一致的，所以就直接从这个开始下手了。为了降低Provider的处理时间，我简单粗暴的把活跃线程数限制死，间接减少并发量。由于不同Provider的最大线程数不同，所以我将(活跃线程数/最大线程数)限制在0.4，没想到直接把分数从1300w干到了1647w，当时人都傻了。后来分析原因也很简单，Gateway这边我们只是根据线程池大小做了简单的加权轮训，所以Gateway这边其实是感知不到Provider的状态的，只是一个冷酷无情的发请求机器。所以看Provider这边的并发量都很大，导致处理时间很长，在Provider限流之后，Provider这边的处理时间就比较低了。

但是写死一个固定的值也不是办法，所以后来我就开始研究限流算法。看了Netflix的concurrency-limits库之后，上了一版基于TCP Vegas的限流算法，但是效果很拉。后来想了下，原因是因为TCP Vegas是基于最小Rtt的，让处理时间在这个最小Rtt附近波动。但是我们比赛的场景是，请求的处理时间随着并发量增大而增大，那最小的请求不就是并发量为1的时候，所以上TCP Vegas直接就把流量限制死了。

这时候留给A榜的时间不多了，所以就没再尝试其他算法，又去做动态探测了。但是在写concurrency-limits的代码分析时意识到，其实可以给最小的Rtt做一个限制的。

# 总结

这次比赛收获还是很大的，一方面是自己技能的收获，至少把之前面试背的负载均衡算法、限流算法的具体实现都看了一遍，顺便也看了看Dubbo的源码。还有就是比赛本身收获，首先就是打比赛，日志画图很重要，清晰的把日志画出对分析赛题帮助非常大；另外就是理性分析也很重要，比如在看完Vegas算法就能想到过度限流的问题，乱尝试还是比较浪费时间的。

# 参考

1. [GitHub - Netflix/concurrency-limits](https://github.com/Netflix/concurrency-limits)
2. [GitHub - alibaba/Sentinel: A powerful flow control component enabling reliability, resilience and monitoring for microservices. (面向云原生微服务的高可用流控防护组件)](https://github.com/alibaba/Sentinel)
3. [[docs]ASoC 2020 中期总结（自适应流控） · Issue #1641 · alibaba/Sentinel · GitHub](https://github.com/alibaba/Sentinel/issues/1641)
4. [集群容错 | Apache Dubbo](https://dubbo.apache.org/zh/docs/advanced/fault-tolerent-strategy/)
5. [负载均衡 | Apache Dubbo](https://dubbo.apache.org/zh/docs/advanced/loadbalance/)
6. [阿里巴巴编程之夏Sentinel中期工作汇总——关于自适应限流](https://www.jianshu.com/p/93a2b9890cc3)
7. [结项报告 · 语雀](https://www.yuque.com/docs/share/887e2a9c-21cd-42a4-a40b-07eced8be3b4?#%20%E3%80%8A%E7%BB%93%E9%A1%B9%E6%8A%A5%E5%91%8A%E3%80%8B)
8. [Go可用性(五) 自适应限流 - Mohuishou](https://lailin.xyz/post/go-training-week6-4-auto-limiter.html)