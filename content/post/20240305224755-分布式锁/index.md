---
title: "分布式锁"
slug: 分布式锁
date: 2024-03-05T22:47:55+08:00
draft: true
---

<!--more-->

# Redis实现

为什么redis可以实现分布式锁呢，首先最重要的特性是，Redis在同一时刻只有一个线程会对一个key进行操作。因此我们可以利用这个特性，让多个服务并发写入一个key，写入成功的服务则认为是成功获得锁了。

这样就完成了锁最重要特性，互斥性，确保一个资源只有一个服务可以拿到。

# 参考

1. [Redis系列(十六)、Redis6新特性之IO多线程_io-threads-do-reads-CSDN博客](https://blog.csdn.net/wsdc0521/article/details/106766587)
2. [Redis 6.0 新特性：带你 100% 掌握多线程模型](https://segmentfault.com/a/1190000040376111)
3. [阿里二面：redis分布式锁过期了但业务还没有执行完，怎么办_redis锁线程没有执行完就过期-CSDN博客](https://blog.csdn.net/m0_67698950/article/details/124461371)