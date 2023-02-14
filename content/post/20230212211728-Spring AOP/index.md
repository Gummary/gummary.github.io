---
title: "Spring AOP简明教程"
slug: Spring-aop
date: 2023-02-12T21:17:28+08:00
draft: true
categories: ["spring"]
tags: ["Java", "Spring", "aop"]
---

<!--more-->


## 2. 核心概念

- *Aspect*:切面，AOP中基本的模块，可以跨越多个不同的类的可执行对象；
- *Joint point*:程序执行的关键点，例如函数调用、异常处理等，在Spring中仅指方法调用；
- *Advice*:切面的执行动作；
- *Pointcut*:判断是否执行切面
- *Introduction*:
- *Target Object*:目标对象
- *AOP Proxy*:目标对象的代理
- *Weaving*:将切面与目标对象代理链接起来。