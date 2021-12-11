---
title: "Dubbo集群总结"
slug: Dubbo集群
date: 2021-12-11T17:04:55+08:00
draft: false
categories: ["Dubbo"]
---

<!--more-->

# 引言

{{< tfigure src="images/cluster.jpeg" title="Cluster调用流程" width="" class="align-center">}}

Dubbo中集群相关的代码在之前的博客中已经处理完了，本文对之前的博客做一个总结。上图是Dubbo集群的主要组成部分，包括服务发现、服务路由、负载均衡及集群容错。在Consumer发起一次调用时，首先通过服务发现获取所有可用的Provider，然后根据自定义的路由配置选出本次调用可用的Provider的，然后通过负载均衡根据当前系统的状态选出最优的Provider，当服务调用失败时使用集群容错策略处理调用失败。

# 如何构造集群？——服务发现

服务发现是构造集群的最基本能力，客户端只有知道远程服务器地址才可以发起远程的PRC调用，因此服务发现是构造集群的过程。在Dubbo3.0之后，Dubbo中同时包含应用级服务发现和接口级服务发现。

- [Dubbo服务目录](/post/dubbo服务路由)

# 所有的Invoker都能用吗？——服务路由

获得所有服务目录之后，根据业务需要，我们可能会手动配置一些路由规则让Consumer调用我们制定的Provider。在Dubbo中共包括条件路由、标签路由等。使用条件路由可以实现服务调用的黑白名单、读写分离、隔离机房等功能；使用标签路由可以对Provider进行分组，让流量仅在一个分组中流转，实现流量隔离。

- [Dubbo服务路由](/post/dubbo服务路由)

# 就决定是你了！——负载均衡

RPC服务最终还是一个客户端和一个服务端之间的调用，因此负载均衡实现的就是根据当前系统的状态从路由结果中选择合适的Provider让Consumer执行。

- [Dubbo负载均衡上](/post/dubbo3负载均衡-上/)
- [Dubbo负载均衡中](/post/dubbo负载均衡中/)
- [Dubbo负载均衡下](/post/dubbo负载均衡下/)

# Oops，调用出错了——集群容错

Dubbo集群容错机制是负载均衡的前置动作，其作用是当某次调用过程失败时，使用某种策略处理失败。

- [Dubbo集群容错](/post/dubbo集群容错/)

# 参考

1. [Dubbo面试杀招--Dubbo集群容错负载均衡](https://blog.csdn.net/qq_35190492/article/details/108778077)
2. [Dubbo 集群容错](https://xie.infoq.cn/article/1b294796a6014a19f06c81bdf)
4. [Dubbo-集群容错(8)](https://www.jianshu.com/p/e2a3b116b5e4)
3. [Dubbo——集群容错(上)](https://www.jianshu.com/p/31438a1d0a04)
5. [Dubbo——集群容错(下)](https://www.jianshu.com/p/2126c1c74304)
6. [服务路由 | Apache Dubbo](https://dubbo.apache.org/zh/docsv2.7/dev/source/router/)
7. [服务导出 | Apache Dubbo](https://dubbo.apache.org/zh/docsv2.7/dev/source/export-service/)