---
title: "Dubbo服务目录"
slug: Dubbo服务目录
date: 2021-10-29T19:46:58+08:00
draft: true
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

# 服务目录源码分析

不介绍staticDirectory

## 列举所有Invoker

## Invoker动态变化

AbstractDirectory


# 参考

1. https://mercyblitz.github.io/2020/05/11/Apache-Dubbo-%E6%9C%8D%E5%8A%A1%E8%87%AA%E7%9C%81%E6%9E%B6%E6%9E%84%E8%AE%BE%E8%AE%A1/
2. https://www.cnblogs.com/caiyao/p/14949139.html
3. https://dubbo.apache.org/zh/docs/concepts/service-discovery/
4. https://dubbo.apache.org/zh/docs/v2.7/dev/source/directory/
5. https://dubbo.apache.org/zh/blog/2021/06/02/dubbo3-%E5%BA%94%E7%94%A8%E7%BA%A7%E6%9C%8D%E5%8A%A1%E5%8F%91%E7%8E%B0/