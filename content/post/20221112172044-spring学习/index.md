---
title: "spring学习"
slug: spring学习
date: 2022-11-12T17:20:45+08:00
draft: true
---

<!--more-->

# Chapter1

Spring是对一些种想软件设计思想的组合及solid、高质量的实现。

**Inversion of Control and Dependency Injection**

控制反转的意思是，之前的框架是由应用程序来控制工作流，而现在是由Spring框架来控制，应用程序的代码是嵌入到Spring框架中的。

Spring中应用控制反转被命名为依赖注入，也即每个组成的依赖都是由框架注入的。

**Aspect-Oriented Programming**

依赖注入可以用于管理POJO，而AOP则是将services应用到这些POJO上。

**Consistent Abstraction**

持久层是用于给AOP服务提供服务的。由Spring来统一管理底层的数据资源。


# Chapter2

## Inversion of Control and Dependency Injection

Spring目前主要的依赖注入方式有三种：Setter Injection,Constructor Injection,Field Injection.

Spring团队推荐Constructor Injection，不推荐Field Injection（原因见可以参考：https://blog.marcnuri.com/field-injection-is-not-recommended）

## Container

Spring中用容器来管理应用和框架中的对象及其生命周期。Spring中的容器称作Bean Factory。

一些Bean Factory：

- BeanFactory，所有Bean factory都要实现的接口
- HierarchicalBeanFactory，在查找bean时会查找parent bean factory
- ListableBeanFactory，允许遍历一个Bean factory下的所有bean。如果有多个层级，则只对当前的bean factory生效
- AutowireCapableBeanFactory，可以自行配置Bean或自己初始化bean，只由spring进行依赖注入。
- ConfigurableBeanFactory，提供一些额外的配置项，用于初始化bean Factory

Application是Spring中的另一种Container，他扩展了Bean Factory的功能，主要区别：

1. 以声明式的方式来实现Bean的注入
2. 可以给Bean发送Event
3. 自动注册BeanFactoryPostProcessor和BeanPostProcessor
4. 实现了ResourceLoader，可以处理低等级的资源。

在Container中Bean的创建方式有三种：

1. 使用new关键字
2. 指定静态工厂方法，工厂方法返回的对象和工厂方法不必相同。
3. 指定非静态工厂方法，先初始化类，再调用该工厂方法。

Bean的生命周期

