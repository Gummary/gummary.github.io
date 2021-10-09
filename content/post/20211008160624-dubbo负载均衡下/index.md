---
title: "Dubbo中的负载均衡策略（下）"
slug: dubbo负载均衡下
date: 2021-10-08T16:06:24+08:00
draft: true
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

在中篇中介绍了最少连接数和最短时间响应两种负载均衡算法，在本篇中介绍Dubbo中最后一种负载均衡算法——一致性Hash算法。我们首先介绍下最基础的Hash算法及其存在的问题，然后介绍一致性哈希算法是如何解决这个问题的，最后介绍一致性哈希负载均衡在Dubbo中的实现。

# 取余哈希算法

假设我们现在有3台节点，我们希望将来源ip地址相同的请求都分配到同一个Provider上。最简单的实现方式是，对来源ip进行hash，然后用hash值对节点数量取余。使用余数选择服务器。


# 一致性哈希算法

# 总结

一致性哈希算法主要解决取余哈希算法中，由于机器伸缩或扩容导致的哈希不一致的问题，减少hash值变动造成的影响。

# 参考

1. https://dgryski.medium.com/consistent-hashing-algorithmic-tradeoffs-ef6b8e2fcae8
2. https://blog.csdn.net/suifeng629/article/details/81567777