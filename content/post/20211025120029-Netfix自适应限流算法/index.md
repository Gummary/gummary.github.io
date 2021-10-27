---
title: "Netfix自适应限流算法"
slug: Netfix自适应限流算法
date: 2021-10-25T12:00:30+08:00
draft: true
---

<!--more-->

# Little's Law

在介绍负载均衡算法之前，先介绍一个基本的定律——Little's Law。

> 在一个稳定的系统中，长期的平均顾客人数（$L$），等于长期的有效抵达率（$\lambda$），乘以顾客在这个系统中平均的等待时间（$W$）
>
> <p align="center">$L = \lambda W$</p>
> <p align="right">维基百科</p>

那么对于我们的一个微服务系统来说，$L$是可以同时处理的请求数量，$\lambda$是当前系统的吞吐率，$W$是每个请求的平均处理时间。而我们系统的承载能力是有限的，所以$L$和$W$是恒定的，那么当请求到达的速度超过了$\lambda$，系统就无法立刻处理这些请求，要么拒绝，要么存放到一个等待队列中等待处理。

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

