---
title: "分布式锁"
slug: 分布式锁
date: 2024-03-05T22:47:55+08:00
draft: true
---

<!--more-->

# Redis实现

## 最简单实现

为什么redis可以实现分布式锁呢，首先Redis的网络模型为Reactor模型，用一个线程处理所有的请求，因此Redis在同一时刻只有一个线程会对一个key进行操作，所以我们可以利用这个特性，让多个服务并发写入一个key，写入成功的服务则认为是成功获得锁了。在服务用完资源后，删除Key即可完成锁释放。

{{< tfigure src="images/redis-thread.png" title="简化reactor模型" width="" class="align-center">}}

在Redis中我们利用SETNX和DROP两个命令就可以实现一个简单的分布式锁。

```shell
SETNX keyname keyvalue
DROP keyname
```

但这种实现会导致死锁问题，如果一个客户端拿到锁后，宕机了，此时其他客户端均无法再获取该锁。为了避免死锁，需要让客户端设置一个过期时间，过期后自动释放锁。

如果客户端预估自己100s完成任务，则将key过期时间设置为100s，即使客户端宕机了，100s后该锁也会释放，不会出现死锁的情况。

```shell
SET keyname keyvalue EX 100 NX
DROP keyname
```


# 参考

1. [Redis系列(十六)、Redis6新特性之IO多线程_io-threads-do-reads-CSDN博客](https://blog.csdn.net/wsdc0521/article/details/106766587)
2. [Redis 6.0 新特性：带你 100% 掌握多线程模型](https://segmentfault.com/a/1190000040376111)
3. [阿里二面：redis分布式锁过期了但业务还没有执行完，怎么办_redis锁线程没有执行完就过期-CSDN博客](https://blog.csdn.net/m0_67698950/article/details/124461371)