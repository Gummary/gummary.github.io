---
title: "Dubbo集群"
slug: Dubbo集群
date: 2021-10-15T20:41:55+08:00
draft: true
---

<!--more-->

# 引言

{{< tfigure src="images/cluster.jpeg" title="Cluster调用流程" width="" class="align-center">}}

在前面的博客中介绍了Dubbo负载均衡算法(上、中、下)，主要解决的是如何从多个Provider中选出一个最优的节点提供服务。在本文中将介绍负载均衡的上层集群层，包括Dubbo中集群的定义，集群容错机制如何处理失败的请求，



本文将对以上其中集群容错策略进行分析，使用的Dubbo源码版本为3.0.

# 如何构造集群？——服务发现

# 所有的Invoker都能用吗？——服务路由

# 就决定是你了！——负载均衡

# Oops，调用出错了——集群容错

Dubbo集群容错机制是负载均衡的前置动作，其作用是当某次调用过程失败时，使用某种策略处理失败，当前可用的集群容错机制如下：

1. AvailableCluster，可用集群容错，调用当前可用的某个Invoker。
2. BroadcastCluster，调用所有的Invoker，当失败的数量达到上限时，停止对剩余invoker的调用。
3. FailBackCluster，失败后一段时间重试
4. FailfasteCluster，失败后直接抛出异常
5. FaileOverCluster，调用失败后，立刻选择另一个invoker重试
6. FailSafeCluster，调用失败后，仅记录失败
7. ForkingCluster
8. MergeableCluster


# 参考

1. https://blog.csdn.net/qq_35190492/article/details/108778077
2. https://xie.infoq.cn/article/1b294796a6014a19f06c81bdf
3. https://www.jianshu.com/p/31438a1d0a04
4. https://www.jianshu.com/p/e2a3b116b5e4
5. https://www.jianshu.com/p/2126c1c74304
6. https://dubbo.apache.org/zh/docsv2.7/dev/source/router/
7. https://dubbo.apache.org/zh/docsv2.7/dev/source/export-service/