---
title: "Dubbo中的服务目录"
slug: Dubbo服务目录
date: 2021-10-29T19:46:58+08:00
draft: false
categories: ["Dubbo"]
---

<!--more-->

# 引言

本文介绍Dubbo集群中的服务目录部分内容。Dubbo服务目录的主要作用是给服务消费者提供服务提供者的信息，供消费者调用。服务目录会监听注册中心的变化，当新增一个服务提供者或某一个服务提供者离线时，服务目录都会更新可用服务提供者的数量。服务注册中心提供给服务目录的是服务提供者的URL信息，在服务目录内部，会将URL转换成一个可实际调用的Invoker对象，供服务消费者使用。

本文将基于Dubbo-java3.0版本介绍服务目录的具体实现，包括调用者如何获取可用的服务提供者及如何处理服务提供者的变更。

# 服务目录类图

先来看下类图，在Dubbo中所有的服务目录都实现了**Directory**接口，在该接口内定义了目录提供的能力，例如获取所有的Invoker、根据调用获取指定服务的Invoker等。

**AbstractDirectory**是Directory接口的唯一实现类，在该类中抽象出一些服务目录共有的功能，同时使用模板模式将服务目录具体的功能下放到子类。

继承AbstractDirectory的服务目录有两个：**StaticDirectory**和**DynamicDirectory**。通过名字我们可以推测出，前者的Invoker不会发生变化，后者的Invoker会发生动态改变，因此后者实现了NotifyListener接口，当注册中心发现服务提供者有更新时，会通过该接口通知服务目录。

对于动态变化的服务目录，有两个子类，分别是**ServiceDiscoryRegistryDirectory**和**RegistryDirectory**。前者是用于Dubbo3.0中新引入的应用级服务发现，后者用于接口级服务发现。

{{< tfigure src="images/directory类图.jpg" title="Directory类图" width="" class="align-center">}}

# 服务目录分析

下面将从服务目录的功能：获取Invoker及动态更新Invoker分析服务目录的源码，由于StaticDirectory比较简单，所以下面分析主要以DynamicDirectory及其子类为主。

## 列举所有Invoker

在RPC调用之前，消费者首先要知道当前可用的服务提供者有哪些，这里就用到了服务能力提供的列举Invoker的能力。整个调用链路如下：

{{< tfigure src="images/列举invoker流程.png" title="列举可用invoker流程" width="" class="align-center">}}

其中当前可用的Invoker列表是保存在AbstractDirectory中，传递到RouterChain进行服务路由后就返回。下面看下可用的Invoker是如何更新的。

## Invoker动态更新

Invoker更新的时机有两处：

1. 服务消费者初始化，获取所有可用的服务提供者时
2. 服务提供者上线、下线时，通知客户端更新可用的Invoker

我们先看下初始化时，服务消费者如何获取可用的服务提供者。

获取Invoker的过程就是服务发现的过程。在Dubbo3.0之前，Dubbo更多使用的是接口级服务发现，Provider每个接口都会在注册中心注册一条数据。在Dubbo3.0中，引入了应用级服务发现，一个服务只在注册中心注册一条数据。这两种服务发现是完全不同的过程，为了平滑过度，在Dubbo3.0中实现了应用级和服务级服务发现的兼容：Provider端具备同时注册接口和应用地址的能力，而Consumer也具备同时发现接口和应用地址的能力。

控制Consumer发现接口还是应用地址的配置是`dubbo.application.service-discovery.migration`，该参数共有三个可选值：

- FORCE_INTERFACE，只消费接口级地址
- APPLICATION_FIRST，智能决策接口级/应用级地址，双订阅
- FORCE_APPLICATION，只消费应用级地址

默认情况下是双订阅模式。在双订阅模式下服务发现的主要流程是：

{{< tfigure src="images/服务发现流程.png" title="双订阅模式下服务发现流程" width="" class="align-center">}}

> 有关应用级服务发现、双订阅/双发布请参阅[服务发现](https://dubbo.apache.org/zh/docs/v3.0/concepts/service-discovery/),[应用级地址发现迁移指南](https://dubbo.apache.org/zh/docs/v3.0/migration/migration-service-discovery/)


# 参考

1. [Apache dubbo 服务自省架构设计 - 小马哥的技术博客](https://mercyblitz.github.io/2020/05/11/Apache-Dubbo-%E6%9C%8D%E5%8A%A1%E8%87%AA%E7%9C%81%E6%9E%B6%E6%9E%84%E8%AE%BE%E8%AE%A1/)
2. [dubbo源码-服务抽象directory - Birding - 博客园](https://www.cnblogs.com/caiyao/p/14949139.html)
3. [服务发现 | Apache Dubbo](https://dubbo.apache.org/zh/docs/concepts/service-discovery/)
4. [服务目录 | Apache Dubbo](https://dubbo.apache.org/zh/docs/v2.7/dev/source/directory/)
5. [Dubbo3 应用级服务发现 | Apache Dubbo](https://dubbo.apache.org/zh/blog/2021/06/02/dubbo3-%E5%BA%94%E7%94%A8%E7%BA%A7%E6%9C%8D%E5%8A%A1%E5%8F%91%E7%8E%B0/)
6. [Dubbo服务引入源码流程 - 掘金](https://juejin.cn/post/6946190804272545805)
7. [集群容错 - Directory | gentryhuang的博客](https://gentryhuang.com/posts/e43ac0a6/)