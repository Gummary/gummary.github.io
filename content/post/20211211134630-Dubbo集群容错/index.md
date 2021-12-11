---
title: "Dubbo集群容错"
slug: Dubbo集群容错
date: 2021-12-11T13:46:30+08:00
draft: false
---

<!--more-->

本文是Dubbo集群的最厚一部分内容，之前的博客中介绍了Dubbo使用服务目录获取可用的Provider，然后通过服务路由得到符合配置的Provider，然后通过负载均衡算法选出最佳的Provider，对该Provider发起RPC调用。但是RPC调用并不是一定成功的，那么如何处理调用失败呢？这就是本文将要讨论的内容，Dubbo中的集群容错策略。

# 集群容错简介

集群容错是指，当rpc调用失败时，处理这个调用失败所采用的机制。Dubbo中共提供了9中集群容错机制，下面是一个总结：

| 容错策略                             | 优点                                   | 缺点                                              | 应用场景                                    |
| :----------------------------------- | -------------------------------------- | ------------------------------------------------- | ------------------------------------------- |
| Failover，调用失败自动重试           | 调用成功率高                           | 调用RT变长                                        | 对调用rt不敏感的场景                        |
| Failfast，失败后抛出给上层           | 业务可以快速感知到调用失败             | 业务需要自行处理报错                              | 由业务处理掉用失败的场景                    |
| Failsafe，不处理失败                 | 不会报错                               | 报错不会抛出，需要自行监控                        | 非核心链路                                  |
| Failback，异步重试                   | 自动异步重试                           | 集群不稳定时，重试任务会堆积                      | 实时性要求低                                |
| Forking，并行发起多个调用            | 调用成功率高                           | 消耗资源，需要保证幂等                            | 资源充足，实时性要求高                      |
| Broadcast，对所有Provider发起掉用    | 可以对所有Provider发起调用             | 消耗资源                                          | 通知所有Provider执行某项操作                |
| Available，只调用一个可用的Invoker   | 不使用负载均衡，业务可以快速感知到失败 | 业务自行处理报错，调用的Invoker可能不是当前最优的 | 不需要负载均衡                              |
| Mergeable，组合多个Invoker的调用结果 | 将一次请求拆分成多个                   | 需要发起多次RPC调用                               | 与Group配合使用，通过分组对调用结果进行组合 |

# 集群容错源码分析

本文以Dubbo默认的集群容错进行分析，

```java
public Result doInvoke(Invocation invocation, final List<Invoker<T>> invokers, LoadBalance loadbalance) throws RpcException {
    // ..
    // 从调用参数中获取充实次数
    int len = calculateInvokeTimes(methodName);
    // retry loop.
    RpcException le = null; // last exception.
    List<Invoker<T>> invoked = new ArrayList<Invoker<T>>(copyInvokers.size()); // invoked invokers.
    Set<String> providers = new HashSet<>(len);
    for (int i = 0; i < len; i++) {
        // 在第一次调用之后，每次都检查Invoker，防止出现变更
        if (i > 0) {
            checkWhetherDestroyed();
            copyInvokers = list(invocation);
            // check again
            checkInvokers(copyInvokers, invocation);
        }
        // 进行负载均衡选出合适的Invoker
        Invoker<T> invoker = select(loadbalance, invocation, copyInvokers, invoked);
        invoked.add(invoker);
        RpcContext.getServiceContext().setInvokers((List) invoked);
        boolean success = false;
        // 开始调用，调用成功则直接返回, 失败则进行下次调用
        try {
            Result result = invokeWithContext(invoker, invocation);
            if (le != null && logger.isWarnEnabled()) {
                logger.warn(/** ... **/);
            }
            success = true;
            return result;
        } catch (RpcException e) {
            if (e.isBiz()) { // biz exception.
                throw e;
            }
            le = e;
        } catch (Throwable e) {
            le = new RpcException(e.getMessage(), e);
        } finally {
            if (!success) {
                providers.add(invoker.getUrl().getAddress());
            }
        }
    }
    throw new RpcException(/** ... **/);
}
```

# 总结

本文介绍了Dubbo中提供的集群容错策略，并分析了默认的集群容错策略的源码。

# 参考文献

1. https://dubbo.apache.org/zh/docs/advanced/fault-tolerent-strategy/
1. https://www.cnblogs.com/zhangyjblogs/p/15073220.html