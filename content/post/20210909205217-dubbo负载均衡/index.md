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

Dubbo负载均衡是在Dubbo框架的第5层（自上而下）Cluster层，客户端根据注册中心提供的服务端列表，根据配置的负载均衡算法选择一个最佳的调用者。本文基于Dubbo3.0.3源码版本介绍Dubbo中原生提供的负载均衡算法。

Dubbo提供的负载均衡算法列表如下：

- RandomLoadBalance，加权随机负载均衡
- RoundRobinLoadBalance，加权轮训负载均衡
- LeastActiveLoadBalance
- ShortestResponseLoadBalance
- ConsistentHashLoadBalance

# 加权随机负载均衡

## 使用

加权随机负载均衡是Dubbo使用的默认负载均衡算法，用户可指定不同服务器的权重，默认权重相同。

不使用权重的情况：TODO

## 实现原理

当没设置权重、权重全相同、权重之和为0时，Dubbo会从Provider中随机选择一个调用。

当权重不为0时，计算权重和S，然后生成一个在[0,S)范围内的随机数，然后判断该随机值位于那个截面上就选择哪一个Provider。

举个例子，假设我们现在有A,B,C三个Provider，权重分别为2,8,1，其权重分布如下图所示。假设生成的随机数为s，若：

- $0\leq s < 2$，则选择服务A；
- $2\leq s < 10$，则选择服务B；
- $10\leq s < 11$，则选择服务C。

{{< figure src="images/2021-09-09-22-03-33.png" title="" width="" class="align-center">}}

# RoundRobinLoadBalance


# 参考文献

1. http://aibenlin.com/algorithm/2019/07/22/algorithm-weight.html