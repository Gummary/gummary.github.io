---
title: "Netfix自适应限流算法"
slug: Netfix自适应限流算法
date: 2021-10-25T12:00:30+08:00
draft: false
---

<!--more-->

# Little's Law

在介绍限流算法之前，先介绍一个基本的定律——Little's Law。

> 在一个稳定的系统中，长期的平均顾客人数（$L$），等于长期的有效抵达率（$\lambda$），乘以顾客在这个系统中平均的等待时间（$W$）
>
> <p align="center">$L = \lambda W$</p>
> <p align="right">维基百科</p>

那么对于我们的一个比如微服务系统来说，$L$是可以同时处理的请求数量，$\lambda$是当前系统的吞吐率，$W$是每个请求的平均处理时间。而我们系统的承载能力是有限的，所以$L$和$W$是恒定的，那么当请求到达的速度超过了$\lambda$，系统就无法立刻处理这些请求，要么拒绝，要么存放到一个等待队列中等待处理。

{{< tfigure src="images/little-law.jpg" title="" width="60%" class="align-center">}}

由于服务器内存等条件的限制，等待队列能承载的请求数量也是有限制的。那么随着请求的数量不断变多，当等待队列也无法承载多余的请求时，就会导致系统的崩溃。所以我们需要引入限流，及时拒绝可能导致系统崩溃的请求。

{{< tfigure src="images/timeout.jpg" title="" width="60%" class="align-center">}}

# 自适应限流

那么如何确定何时开始限流呢？最简单的办法是，根据当前服务器的性能，如CPU数量、内存大小等设定一个经验值，当当前并发处理的请求数量或队列中请求的数量到达设定的经验值时就拒绝之后的请求，及时保护系统。但是不同的服务业务逻辑不同，处理请求的速度也不同，因此仅仅根据服务器硬件得到的经验值可能并不适合当前服务器。

另一种方式是进行数据统计，在不限流的情况下测试服务器的承载能力，然后根据统计结果得到一个限流值。但是在每次服务器进行扩容，或修改业务逻辑时，都需要重新进行统计。

因此为了更好的应对服务器变化，需要一种自适应的方式，根据服务器的响应时间等信息动态的更改限流值。如下图所示，从一个初始值开始，不断增大limit的值，当处理请求的延迟增大到一定程度时，减少limit的值，使limit收敛到服务器真实的承载能力附近。

{{< tfigure src="images/adaptive.jpg" title="" width="60%" class="align-center">}}

# Netfix 自适应限流库

[concurrency-limit](https://github.com/Netflix/concurrency-limits)是Netfix推出的一个自适应限流工具包，提供了很多自适应限流算法，下面本文将介绍其中的Gradient、Gradient改进版本及Vegas限流算法。

## Gradient限流算法

Gradient限流算法是计算无负载时的RTT与当前RTT的比值来判断是否出现请求排队的情况。令$\text{gradient} = \text{RTTNoLoad} / \text{RTTactural}$，则当gradient等于1时，说明当前请求没有排队；当gradient小于1时，说明当前开始排队了，需要降低limit。所以limit的更新方式是：

$$
\text{newLimit} = \text{currentLimit} \times \text{gradient} + \text{queueSize}
$$

其中queueSize可以允许出现一定的排队，一般将该值设置为当前limit的平方根。选择平方根的原因是，对于小的limit，其增长很快，在探测阶段可以随着limit快速增长；当limit增大时，其变动又会比较平稳，有更好的稳定性。

## Gradient2限流算法

Gradient限流算法实现简单，但其忽略了一点是业务处理时间可能会发生变化。例如在RPC调用中，请求参数量多的请求通常比请求参数量低的请求处理时间长。而Gradient限流算法在这种情况下就会出现过度保护的问题。虽然RTT很低，但是通过的请求量也会变少。

Gradient2算法将noLoadRTT设置为RTT的指数移动平均，会随着RTT的增大而增大，缓解了过度保护的情况。Gradient2计算Gradient的方式变为：

$$
\begin{aligned}
	\text{LongRTT}_ t &= (1-\frac{1}{w}) \times \text{LongRTT}_{t-1} + \frac{1}{w} \times \text{RTT}_t \\\\
	\text{gradient} &= \text{Max}(0.5, \text{Min}(1, \frac{\text{LongRTT}_ t}{\text{RTT}_t}))
\end{aligned}
$$

其中w为请求窗口的大小。此时系统有三种可能的状态：

1. 平稳状态，limit在系统的真实负载附近波动；
2. 从平稳态进入过载状态，此时RTT逐渐变大，而LongRTT也会随着RTT变大不断变大，为了防治出现一个非常大的延迟使limit下降的非常快，这里将gradient的最小值设置为0.5。
3. 从过载状态恢复平稳状态，此时可能出现RTT比LongRTT更低的情况，这种情况视为不需要排队的情况，所以将gradient的最大值设置为1。

## Vegas负载均衡算法

Vegas限流算法是启发自TCP的Vegas 拥塞避免算法，下面先介绍下Vegas拥塞避免算法。

**Vegas拥塞避免算法**

TCP Reno的网络拥塞检测是通过是否丢包来判断的，当出现丢包时认为网络出现了拥塞，开始进行拥塞避免。而TCP Vegas算法是根据RTT来判断网络是否出现拥塞。具体来说Vegas会记录网络中出现的最小RTT作为无拥塞情况的RTT，用该RTT计算期望吞吐率，与实际的吞吐率作差，当差值较小时增大窗口,差值较大减少窗口。

$$
\begin{aligned}
	\text{Expected} &= \text{cwnd} / \text{RTTNoLoad} \\\\
	\text{Actual} &= \text{cwnd} / \text{RTT} \\\\ 
	\text{diff} &= \text{Expected} - \text{Actual}
\end{aligned}
$$

$$
\begin{cases}
	\text{diff} &< \alpha, \quad 扩大窗口 \\\\
	\text{diff} &> \beta, \quad 缩小窗口 \\\\
\end{cases}
$$

其中cwnd为当前窗口的大小。

**Vegas限流算法**

与TCP Vegas使用差值判断是否拥塞不同的是，Vegas限流算法直接使用等待队列的大小queueSize进行判断是否限流。另外，在TCP Vegas中，$\alpha$和$\beta$的值是固定不变的，为了让限流算法在高limit时有更好的稳定性，Vegas限流算法会根据当前limit动态调整这两个值。

计算调整阈值的函数为：

$$
\begin{aligned}
	\alpha &= 3\text{log}_ {10}^{\text{limit}} \\\\
	\beta &= 6 \text{log}_ {10}^{\text{limit}} \\\\
	\text{threshold} &= \text{log}_ {10}^{\text{limit}} 
\end{aligned}
$$

动态调整限流值的方法为：

$$
\ \text{newLimit} = 
\begin{cases}
	limit + \beta, &\quad \text{queueSize} < \text{threshold} \\\\
	limit + \text{log}_ {10}^{\text{limit}}, &\quad \text{threshold} < \text{queueSize} <\alpha \\\\
	limit - \text{log}_ {10}^{\text{limit}}, &\quad \text{queueSize} > \beta \\\\
	limit, &\quad 其他
\end{cases}
$$

其中计算队列大小的方式是：

$$
\text{queueSize} = \text{limit} \times (1 - \text{RttnoLoad}/ \text{RTTactual})
$$

对于Vegas这种限流算法来说，也会存在过度保护的情况。

# 参考

1. [Fairness Comparisons Between TCP Reno and TCP Vegas for Future
Deployment of TCP Vegas](https://web.archive.org/web/20160103040648/http://www.isoc.org/inet2000/cdproceedings/2d/2d_2.htm#s2)
2. [TCP拥塞控制 - 维基百科，自由的百科全书](https://zh.wikipedia.org/wiki/TCP%E6%8B%A5%E5%A1%9E%E6%8E%A7%E5%88%B6)
3. [自适应限流神器 netflix-concurrency-limits](https://fredal.xin/netflix-concuurency-limits)
4. [Performance Under Load. Adaptive Concurrency Limits @ Netflix | by Netflix Technology Blog | Medium](https://netflixtechblog.medium.com/performance-under-load-3e6fa9a60581)
5. [GitHub - Netflix/concurrency-limits](https://github.com/Netflix/concurrency-limits)