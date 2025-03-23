---
title: "分布式锁"
slug: 分布式锁
date: 2024-03-05T22:47:55+08:00
draft: true
---

<!--more-->

# Redis实现

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

使用这种过期的方式还有一个问题，客户端需要自己预估时间，但这个时间往往不准，可能没处理完就释放或提前结束但一直持有锁。这种情况下可以启动一个守护线程，守护线程定期监控锁是否释放，如果没有就对锁进行续租。


目前对redis进行加锁使用的都是同一个keyvalue，一个线程加锁后，其他线程也有可能直接释放锁，这种情况下每个线程都要设置一个独一无二的keyvalue，在释放锁前先判断value的值是否是自己加锁时设置的，如果是才能释放。

这个过程有一个先读后写的操作，为了避免并发问题，通常将该逻辑放到一个lua脚本里：

```lua
if redis.call("get",KEYS[1]) == ARGV[1] then
    return redis.call("del",KEYS[1])
else
    return 0
end
```

目前讨论的分布式锁都是基于单机情况下，为了避免单点故障，redis通常有多个实例。在这种情况下，redis可能会出现丢失锁的问题。例如客户端在获取锁后，主节点还没同步给从节点就下线了，新的主节点就没有该锁，导致其他客户端也能获取到该锁。

针对该问题，redis作者提出了一个[redlock算法](https://redis.io/docs/manual/patterns/distributed-locks/)。






# 参考

1. [Redis系列(十六)、Redis6新特性之IO多线程_io-threads-do-reads-CSDN博客](https://blog.csdn.net/wsdc0521/article/details/106766587)
2. [Redis 6.0 新特性：带你 100% 掌握多线程模型](https://segmentfault.com/a/1190000040376111)
4. https://heapdump.cn/article/5509526