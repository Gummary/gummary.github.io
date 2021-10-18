---
title: "Dubbo集群容错"
slug: Dubbo集群容错
date: 2021-10-15T20:41:55+08:00
draft: true
---

<!--more-->

Dubbo将所有的Provider抽象为一个集群，当调用集群失败时，将触发集群容错机制，可用的集群容错策略如下：

1. AvailableCluster
2. BroadcastCluster，广播
3. FaileBackCluster
4. FaileOverCluster
5. FailSafeCluster
6. ForkingCluster
7. MergeableCluster

本文将对以上其中集群容错策略进行分析，使用的Dubbo源码版本为3.0.