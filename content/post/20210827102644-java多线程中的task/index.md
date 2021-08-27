---
title: "Java多线程中的task"
slug: java多线程中的task
date: 2021-08-27T10:26:44+08:00
draft: true
---

# 从接口说起

在Java中，要在一个线程中运行一段代码，需要一个对象实现Runnable，Callable接口，然后将该类作为参数构造一个Thread并start。或者继承Thread类，直接start。其实本质上，Thread类也是实现了Runnable接口。所以我们重点关注Runnable和Callable接口。

## Runnable接口

先看Runnable接口，Runnable接口其实是非常简单的，其源码为：

```java
public interface Runnable {
    public abstract void run();
}
```

这个接口的作用也非常简单，用来创建一个新的线程，然后在新的线程中执行run中的方法。下面举一个简单的例子，创建一个线程，实现1-100的累加。

```java
// 实现Runnable接口
public class SumRunnable implements Runnable{

    /**
     * 线程执行入口
     */
    @SneakyThrows
    @Override
    public void run() {
        int result = 0;
        for (int i = 0; i < 100; i++) {
            result += i;
        }
        System.out.println(result);
    }

    public static void main(String[] args) {
        SumRunnable sum = new SumRunnable();
        new Thread(sum).run();
    }
}
```

## Callable接口

Runnable接口虽然简单，但是这也导致其提供的功能是比较小的。比如，我们不希望在另一个线程内打印结果，我们要把打印的部分收敛到主线程。这就要求计算线程能将结果传给主线程。如果使用Runnable来实现，那就要我们自己实现一套线程同步机制，传递计算结果。

Runnable接口的缺失的一个能力就是**没有返回值**；另外，Runnable接口也无法抛出已检异常。

我们来看下Callable的源码：

```java 
public interface Callable<V> {
    V call() throws Exception;
}
```

可以看到，Callable接口比Runnable接口多了返回值并抛出异常。下面仍然以求和举例：

```java
public class SumCallable implements Callable<Integer> {
    @Override
    public Integer call() throws Exception {
        int result = 0;
        for (int i = 0; i < 100; i++) {
            result += i;
        }
        return result;
    }

    public static void main(String[] args) throws ExecutionException, InterruptedException {
        SumCallable sum = new SumCallable();
		// 创建线程池
        ExecutorService executor = Executors.newFixedThreadPool(1);
		// 提交任务
        Future<Integer> future = executor.submit(sum);
		// 获取任务返回结果
        Integer integer = future.get();
        System.out.println(integer);
    }
}
```

我们首先创建了一个线程池，然后将求和的类提交给线程池，线程池返回给我们一个`Future`对象，我们从这个Future对象中得到了我们计算的结果。那么这个新引入的Future对象的作用是什么？在参数传递的过程中扮演了怎样的角色呢？

## Future接口

# FutureTask又是什么？

是runnable和callable的结合体，也是RunnableFuture的具体实现。

# Java8新特性-CompletableFuture


1. https://www.liaoxuefeng.com/wiki/1252599548343744/1306581182447650
2. https://zhuanlan.zhihu.com/p/54459770
3. https://www.cnblogs.com/nullzx/p/5147004.html
4. https://www.cnblogs.com/dolphin0520/p/3949310.html
5. JCIP 6.3.2