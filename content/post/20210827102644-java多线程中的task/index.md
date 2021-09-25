---
title: "Java多线程中的task"
slug: java多线程中的task
date: 2021-08-27T10:26:44+08:00
draft: false
---

<!--more-->

# 从接口说起

在Java中，要在一个线程中运行一段代码，需要一个对象实现Runnable或Callable接口，然后将该类作为参数传给一个线程运行；或者继承Thread类，直接start运行。其实本质上，Thread类也是实现了Runnable接口，在运行时运行重载的run方法。所以我们就先从Runnable和Callable接口说起。

## Runnable接口

先看Runnable接口，Runnable接口其实是非常简单的：

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

Runnable接口虽然简单，但是其提供的功能相对就很少的。如果我们不希望在另一个线程内打印结果，我们要把打印的部分收敛到主线程。这就要求计算线程能将结果传给主线程。如果使用Runnable来实现，那就要我们自己实现一套线程同步机制，传递计算结果。所以Runnable接口最大的缺点在于不能直接获得执行结果；另外，Runnable接口也无法获取任务执行中发生的异常。

于是，在Java1.5中新加入了Callable接口，我们来看下Callable的源码：

```java 
public interface Callable<V> {
    V call() throws Exception;
}
```

可以看到，Callable接口可以返回返回值并抛出异常。下面仍然以求和举例：

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

我们在将任务提交给线程池后，线程池返回给我们一个`Future`对象，我们通过`get`得到任务执行结束后返回的结果。所以其实`Future`的主要作用就是给我们提供了一种方式让我们可以获得另一个线程的执行结果。但`Future`的作用远不止如此，我们先来看下`Future`接口都提供了哪些方法。

```java
public interface Future<V> {
    boolean cancel(boolean mayInterruptIfRunning);
    boolean isCancelled();
    boolean isDone();
    V get() throws InterruptedException, ExecutionException;
    V get(long timeout, TimeUnit unit)
        throws InterruptedException, ExecutionException, TimeoutException;
}
```

可以看到，除了获取结果外，`Future`还给我们提供了判断任务是否结束、是否取消、和取消任务的能力。我们下面来看下各个方法的作用。

`cancel()`方法可以用来取消一个任务。对于未执行的task，task直接进入结束状态，并且永远不会执行。对于已经开始运行的任务，cancel通过`mayInterruptIfRunning()`参数控制是否立刻中断task还是等待任务自然结束。如果task已经结束，无论是自然结束还是被中断，`cancel`会返回`false`表示取消执行失败。

`isCancelled()`方法用于判断一个任务是否在正常结束之前被取消了。

`isDone()`方法用一个判断一个任务是否完成。这里的完成包括了正常结束，或在运行期间抛出异常，或被取消。

`get()`方法是`Future`的核心方法，用于获取一个异步线程的结果。调用该方法后，调用线程会阻塞，直到任务结束。如果任务正常结束，则`get()`会返回结果；如果任务被取消，`get()`会抛出`CancellationException`异常；如果任务执行时抛出了异常，那`get()`方法会抛出`ExecutionException`异常，通过`getCause()`方法可以得到抛出的异常；如果**当前线程**在等待执行结果时被中断了，会抛出`InterruptedException`异常。

`get(long timeout, TimeUnit unit)`是`get()`方法的重载方法，允许当前线程等待指定的时间后，如果任务还没有结束并返回，那么会抛出`TimeoutException`异常。

所以其实`Future`方法不仅仅提供了一个获取结果的方式，其实还代表了一个任务的生命周期，让我们可以知道任务当前是什么状态。但是`Future`毕竟只是一个接口，最终的行为还是取决于具体的实现，所以我们接下来就看一下Java提供的`Future`实现类——`FutureTask`。

# Future的具体实现——FutureTask

我们先来看下`FutureTask`的类图，他同时实现了Runnable和Future两个接口。

{{< tfigure src="images/FutureTask.png" title="FutureTask类图" width="40%" class="align-center">}}

那么就是说，当`FutureTask`提交给另一个线程执行时，其实运行的是`Runnable`的`run()`方法。我们下面来看下他的构造函数和`run()`方法：

```java
public FutureTask(Runnable runnable, V result) {
    this.callable = Executors.callable(runnable, result);
    this.state = NEW;       // ensure visibility of callable
}

public FutureTask(Callable<V> callable) {
    if (callable == null)
        throw new NullPointerException();
    this.callable = callable;
    this.state = NEW;       // ensure visibility of callable
}

public void run() {
        // ...
        try {
            Callable<V> c = callable;
            if (c != null && state == NEW) {
                V result;
                boolean ran;
                try {
                    result = c.call();
                    ran = true;
                } catch (Throwable ex) {
                    result = null;
                    ran = false;
                    setException(ex);
                }
                if (ran)
                    set(result);
            }
        } finally {
            // ...
        }
    }
```

所以他是以`Callable`为参数，在`run()`中执行`Callable`，然后返回执行结果。

上面是实现`Runnable`接口的部分，下面来看下实现`Future`接口的部分，先来看下核心的`get()`方法：

```java
public V get() throws InterruptedException, ExecutionException {
    int s = state;
    if (s <= COMPLETING)
        s = awaitDone(false, 0L);
    return report(s);
}

public V get(long timeout, TimeUnit unit) throws InterruptedException, ExecutionException, TimeoutException {
    if (unit == null)
        throw new NullPointerException();
    int s = state;
    if (s <= COMPLETING &&
        (s = awaitDone(true, unit.toNanos(timeout))) <= COMPLETING)
        throw new TimeoutException();
    return report(s);
}
```

不论是阻塞的`get()`还是有超时的`get()`，最后都会调用`awaitDone()`方法。下面是`awaitDone()`方法的结构体，看下面代码之前我们需要记住，调用`get()`方法的线程和执行`run()`方法的线程不是一个线程。下面的`WaitNode`是一个单链表,用于存放等待当前任务执行结果的线程，每当有一个线程调用`FutureTask`的`get()`方法时，就会初始化一个`WaitNode`并将自己加入到该链表中。

```java
private int awaitDone(boolean timed, long nanos)
    throws InterruptedException {
    final long deadline = timed ? System.nanoTime() + nanos : 0L;
    WaitNode q = null;
    boolean queued = false;
    for (;;) {
        // 先判断执行get的线程是否被中断，如果中断则从链表中移除
        if (Thread.interrupted()) {
            removeWaiter(q);
            throw new InterruptedException();
        }

        int s = state;
        if (s > COMPLETING) { 
            // 线程已经结束，返回
            if (q != null)
                q.thread = null;
            return s;
        }
        else if (s == COMPLETING) // 线程正在结束，需要设置结果或设置异常，当前线程让出CPU，等待下次循环
            Thread.yield();
        else if (q == null) // 当前线程第一次调用get方法，初始化一个WaitNode变量
            q = new WaitNode();
        else if (!queued) // WaitNode已初始化，加入到等待队列中；这里采用的是头插法。
            queued = UNSAFE.compareAndSwapObject(this, waitersOffset,
                                                    q.next = waiters, q);
        else if (timed) {
            // 如果是有时间中断的，那么等待指定时间
            nanos = deadline - System.nanoTime();
            if (nanos <= 0L) {
                // 等待时间够了，移出等待队列
                removeWaiter(q);
                return state;
            }
            // 阻塞剩余的时间
            LockSupport.parkNanos(this, nanos);
        }
        else
            LockSupport.park(this); // 当前线程阻塞，直到任务运行结束。
    }
}
```

我们再来看一下`cancel()`方法：

```java
public boolean cancel(boolean mayInterruptIfRunning) {
    // 判断是否可以执行中断，这里是对状态为NEW的任务进行处理
    // 如果一个任务的状态为NEW，并且可以将状态设置为INTERRUPTING或CANCELLED，那么返回True
    // 如果这个过程失败了，返回false
    if (!(state == NEW &&
            UNSAFE.compareAndSwapInt(this, stateOffset, NEW,
                mayInterruptIfRunning ? INTERRUPTING : CANCELLED)))
        return false;
    try {    // in case call to interrupt throws exception
        // 尝试中断正在执行的任务
        if (mayInterruptIfRunning) {
            try {
                Thread t = runner;
                if (t != null)
                    t.interrupt();
            } finally { // final state
                UNSAFE.putOrderedInt(this, stateOffset, INTERRUPTED);
            }
        }
    } finally {
        // 任务完成
        finishCompletion();
    }
    return true;
}
```

在出现异常、任务完成、任务取消的时候，都会调用`finishCompletion()`方法，该方法的作用是遍历等待队列并唤醒在等待队列中的线程们。

# 更强大的CompletableFuture类

虽然`FutureTask`实现的Future接口能够让我们获取进程运行的返回值，但是FutureTask有个最大的问题在于，我们无法获得FutureTask准确结束的时间。如果我们要获得FutureTask的返回值并对结果进行处理，要么不断调用`get()`方法阻塞当前线程，要么不断调用`isDone()`方法，等待任务完成。二者都会阻塞当前线程。

另外`FutureTask`其实仅仅代表了一个任务，如果需要组合多个并行的任务，比如连续执行任务A，任务B，任务C，就需要创建三个FutureTask并阻塞当前线程三次；或者任务A和任务B并行执行，二者都结束后执行任务C，那么就需要在主线程中等待两个任务结束，再创建一个FutureTask执行任务。

因此，Java 8添加了一个新的Future实现类——CompletableFuture，加入了更多的新功能：

1. 手动结束任务，允许用户不提供运行的代码，只提供结果即可结束一个任务。
2. 允许传递回调函数。
3. 自由组合多个任务。

## 手动结束任务

如果我们要使用一个FutureTask，那么必须要给该类提供一个实现Callable或Runnable接口的类才行。而CompletableFuture允许开发者直接调用complete手动结束Future，我们仍然以求和为例：

```java
public class SumCompeletableFuture {

    public static Integer sum() {
        // ...
    }

    public static void main(String[] args) throws ExecutionException, InterruptedException {
        CompletableFuture<Integer> future = new CompletableFuture<>();
        new Thread(() -> {
            Integer result = SumCompeletableFuture.sum();
            // 在另一个线程内手动结束任务
            future.complete(result);
        }).run();
        System.out.println(future.get());
    }
}
```

上述代码还可以结合Lambda表达式简化为：

```java
public class SumCompeletableFuture {

    public static Integer sum() {
        // ...
    }

    public static void main(String[] args) throws ExecutionException, InterruptedException {
        CompletableFuture<Integer> future = CompletableFuture.supplyAsync(SumCompeletableFuture::sum);
        System.out.println(future.get());
    }
}
```

其中`CompletableFuture.supplyAsync`会使用`ForkJoinPool`默认的线程池执行。CompletableFuture的各种方法也允许开发者使用自定义的线程池。

## 允许回调函数

CompletableFuture另一个增强是允许用户使用`thenAccept`传递回调方法，当任务结束时，自动调用该回调方法。

比如我们可以将上述代码改为：

```java
public class SumCompeletableFuture {

    public static Integer sum() {
        // ...
    }

    public static void main(String[] args) throws ExecutionException, InterruptedException {
        CompletableFuture<Integer> future = CompletableFuture.supplyAsync(SumCompeletableFuture::sum);
        // 自动回调打印任务
        future.thenAccept(System.out::println);
    }
}
```

## 组合多个任务

这个应该是`CompletableFuture`带来的最为强大的功能了。

`CompletableFuture`允许组合两个串行执行的任务，然后利用二者的结果执行回调函数。该功能的函数为`thenCompose`，`thenCompose`默认执行的线程是上一个任务的线程，可以减少线程切换的损耗。但CompletableFuture仍提供了一个兄弟方法`thenCombineAsync`，将会使用一个新的线程执行该任务。

thenCompose的第一个参数是要串行执行的`CompletableFuture`，第二参数是一个以二者返回值为参数的`BiFunction`,thenCombine的返回值是一个新的CompletableFuture。

```java
public class SumCompose {
    public static void main(String[] args) throws ExecutionException, InterruptedException {
        CompletableFuture<Integer> task = CompletableFuture.supplyAsync(Sum::sum);
        CompletableFuture<Integer> future = task.thenCombine(
                CompletableFuture.supplyAsync(Sum::sum),
                Integer::sum
        );
        System.out.println(future.get());
    }
}
```


CompletableFuture还可以将多个CompletableFuture任务组合到一起并发执行。比如我们用一个Task执行1-50的求和，另一个任务执行51-100的。如果使用`FutureTask`我们需要手动管理二者的关系，使用`CompletableFuture`我们可以直接调用thenCombine。thenCombine的第一个参数是要并发执行的`CompletableFuture`，第二参数是一个以二者返回值为参数的`BiFunction`,thenCombine的返回值是一个新的CompletableFuture。

```java
public class SumCombine {

    public static void main(String[] args) throws ExecutionException, InterruptedException {
        CompletableFuture<Integer> task = CompletableFuture.supplyAsync(Sum::sum);
        CompletableFuture<Integer> future = task.thenCombine(CompletableFuture.supplyAsync(Sum::sum), Integer::sum);
        System.out.println(future.get());
    }
}
```

CompletableFuture还提供了很多方法，具体这里不再展开，其他函数可参考[Java doc](https://docs.oracle.com/javase/8/docs/api/java/util/concurrent/CompletableFuture.html)

# 总结

ok，以上就是本文的全部内容，本文首先从线程执行相关的接口讲起，介绍了无返回值的Runnable接口和有返回值的Callable接口，然后介绍了用于获取返回值的Future接口并重点分析了Future的实现类FutureTask的源码。最后介绍了Java8中新提供的CompelableFutureTask的使用。

# 参考

1. https://www.liaoxuefeng.com/wiki/1252599548343744/1306581182447650
2. https://zhuanlan.zhihu.com/p/54459770
3. https://www.cnblogs.com/nullzx/p/5147004.html
4. https://www.cnblogs.com/dolphin0520/p/3949310.html
5. JCIP 6.3.2
6. https://www.cnblogs.com/daxin/p/3366606.html
7. https://github.com/JetBrains/jdk8u_jdk/blob/master/src/share/classes/java/util/concurrent/RunnableFuture.java
8. https://github.com/frohoff/jdk8u-jdk/blob/master/src/share/classes/java/util/concurrent/FutureTask.java