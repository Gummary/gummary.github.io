---
title: "Dubbo中的时间轮算法"
slug: Dubbo中的时间轮算法
date: 2021-09-13T14:23:35+08:00
draft: true
categories: ["Dubbo"]
---

<!--more-->

# 时间轮算法简介

// 是什么
时间轮算法是一种非常巧妙、高效的延迟任务调度系统，其算法模型与圆盘手表非常类似。

时间轮的数据结构主要由一个环形队列，一个队列指针，多个双向链表组成。

{{< figure src="images/2021-09-13-16-00-21.png" title="时间轮模型" width="" class="align-center">}}

环形队列是时间轮的核心结构，队列上的每个节点是一个槽(bucket)，每个槽代表了一段时间间隔(duration)。在每个槽中都存储一个双向链表的头节点，而双向链表中的每个节点代表了实际执行的任务。队列指针指向的是当前时刻的槽。

那么时间轮算法是如何运行的呢。时间轮启动时，从第一个槽，0号槽开始运行，假设每个槽的时间间隔为1s，那么每经过1s，队列指针就会向下一个槽移动。然后开始遍历当前槽的任务队列，执行任务队列中的任务。

当有延迟任务要加入到时间轮中时，会首先根据时间间隔计算出应该加入到哪一个槽中，然后将该任务加入到该队列中。

但是这样做又一个问题是，比如我们的时间轮现在有12个槽，时间间隔为1s，当前我们在0号槽，那么我们的时间轮最多只能存储未来12秒内的任务，如果我们插入一个需要在13秒执行的任务，那么就会被插入到第1号槽，在下一次调度的时候就会被执行，这就不符合我们的预期了。

解决这个“套圈”问题的方法通常有两个，一个是用多个嵌套的时间轮，内部时间轮的间隔是最小的，而外层的时间轮每个槽的间隔是内层时间轮一圈的时长，类似于我们现实时钟里的时分秒的概念。Kafka中的时间轮算法就采用了这种方式。

还有一种方法是在每个任务中新增一个轮次的字段，表示第几次转到当前槽时执行当前任务。Netty和Dubbo中使用这种方式。

时间轮的缺点是，不能精确的描述一个任务，其任务调度的最小间隔取决于时间槽的间隔。

# Dubbo中的时间轮算法

在有了时间轮的基本概念后，我们看下在Dubbo中是如何实现时间轮算法的。我们先来看一下Dubbo中与时间轮算法相关类的类图：

{{< figure src="images/2021-09-18-20-56-58.png" title="时间轮类图" width="" class="align-center">}}

## 接口

**Timer接口**是Dubbo中的定时器接口，提供了三个方法：

- newTimeout方法用于向Timer提交一个TimerTask，然后返回一个Timeout句柄，是Timer的核心方法。
- stop停止当前定时器，返回所有被取消的TimerTask。
- isStop用于判断当前定时器是否停止。

**Timeout接口**是一个定时任务的句柄，向定时器提交一个定时任务后，会返回该接口的实现类，通过该类提交者可以判断任务的状态：

- 使用isExpired判断一个定时任务是否执行。
- 使用isCancelled判断一个定时任务是否被取消。
- cancel可以取消一个定时任务

**TimerTask接口**是Dubbo中定时任务的接口，用户定义定时器任务并实现该接口后就可以向Timer提交任务，在设定的时间后就会执行run方法。

Timeout和TimerTask之间的关系其实类似于FutureTask和线程池之间的关系。

## 具体实现

**HashedWheelTimer**（时间轮定时器）在Dubbo中是Timer接口的唯一实现。其核心结构是由HashedWheelBucket数组组成的一个环形列表，HashedWheelBucket中包含一个由HashedWheelTimeout组成的双向链表。其中HashedWheelBucket是时间槽，HashedWheelTimeout是任务句柄。下面我们就看下HashedWheelTimer的具体实现。

在构造函数中，主要初始化时间轮的时间槽，然后使用构造函数中传递的线程工厂创建一个新线程执行Worker的run方法。其中初始化时间槽的时候会将时间槽的长度设置为$2^N, N < 30$，目的是为了根据任务的延迟时间快速定位到时间槽。Worker是进行时间槽轮转的工具人类，在其run方法中实现了时间轮的推进。


在newTimeout方法中，首先会调用启动函数，如果当前定时器未启动，则启动当前定时器。然后计算出该任务的Deadline，根据Deadline和TimeTask构造出一个HashedWheelTimeout，将HashedWheelTimeout加入到待处理的Timeout队列中。

```java
public Timeout newTimeout(TimerTask task, long delay, TimeUnit unit) {
	// ...

	start();
	// timeout的deadline是执行时间与时间轮运行时间的差，方便之后计算推进的次数
	long deadline = System.nanoTime() + unit.toNanos(delay) - startTime;
	// ...
	HashedWheelTimeout timeout = new HashedWheelTimeout(this, task, deadline);
	timeouts.add(timeout);
	return timeout;
}
```

下面我们来分析下Worker类，该类是HashedWheelTimer的内部类。我们直接从该类的run方法看起：

在run中用一个循环不断推进时间轮，在每个循环中按顺序完成以下工作：

1. 等待一次推进的时间
2. 通过位运算直接定位到当前的槽函数
3. 处理被取消的任务
4. 将在待处理的任务队列中任务加入到对应的槽函数中
5. 处理当前槽的任务
6. 推进一格时间槽

```java
public void run() {
	// 初始化过程...

	do {
		final long deadline = waitForNextTick();
		if (deadline > 0) {
			int idx = (int) (tick & mask);
			processCancelledTasks();
			HashedWheelBucket bucket = wheel[idx];
			transferTimeoutsToBuckets();
			bucket.expireTimeouts(deadline);
			tick++;
		}
	} while (WORKER_STATE_UPDATER.get(HashedWheelTimer.this) == WORKER_STATE_STARTED);

	// 将未处理的任务加入到unprocessedTimeouts中...
}
```

processCancelledTasks中会不断轮训cancelledTimeouts队列，将所有取消的任务都从对应槽的双向链表中移，直至cancelledTimeouts为空。

transferTimeoutsToBuckets方法将待处理的timeout加入到时间槽的双向队列中：

```java
private void transferTimeoutsToBuckets() {
	// 每次只加100000个任务到时间槽中，防止某个线程不停的向时间轮中提交任务。
	for (int i = 0; i < 100000; i++) {
		HashedWheelTimeout timeout = timeouts.poll();
		if (timeout == null) {
			// 全部处理完成
			break;
		}
		if (timeout.state() == HashedWheelTimeout.ST_CANCELLED) {
			// 如果timeout被取消了，则直接跳过
			continue;
		}

		// 计算出到timeout的deadline之前需要几次推进
		long calculated = timeout.deadline / tickDuration;
		// 根据推进的次数计算出还需要几轮
		timeout.remainingRounds = (calculated - tick) / wheel.length;

		// 确保是未来的任务
		final long ticks = Math.max(calculated, tick);
		// 计算出槽的下标
		int stopIndex = (int) (ticks & mask);
		// 将timeout加入到对应槽的双向队列中
		HashedWheelBucket bucket = wheel[stopIndex];
		bucket.addTimeout(timeout);
	}
}
```



相关类Timer，Timeout，HashedWheelTimer，HasedWHeelTimeout，Worker，HashedWheelBucket，TimerTask

HashedWheelTimer中是Timer的唯一实现类，时间槽的数量是2^N,通过mask可以快速定位到槽位置。

# 参考文献

1. https://www.cnblogs.com/luozhiyun/p/12075326.html
2. https://segmentfault.com/a/1190000023832602
3. https://juejin.cn/post/6844904110399946766