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

# 最短相应时间负载均衡算法

