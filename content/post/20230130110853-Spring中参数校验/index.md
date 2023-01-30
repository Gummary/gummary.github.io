---
title: "Java Bean Validation with Spring Boot"
slug: java-bean-validation-with-spring-boot
date: 2023-01-30T11:08:53+08:00
draft: true
categories: ["spring"]
tags: ["Java", "Spring"]
---

在应用程序中，为了确保程序运行正确，通常需要对用户输入进行校验。Java中为了对Bean进行校验先后发布了JSR 303、JSR 349、JSR 380，帮助Java开发者快速校验Java Bean。作为Java应用开发中的主流框架Spring，也大量使用了Java Bean Validation。本文先简单介绍Java Bean Validation的发展历史，然后介绍在Spring中如何应用，最后介绍Spring中Bean Validation的实现原理。

<!--more-->

# Java Bean Validation发展历史

Emmanuel Bernard在2009年发布了JSR 303（Bean Validation 1.0），在该标准中定义了如何使用注解对JavaBean进行校验；Emmanuel于2013年又发布了JSR 349（Bean Validation 1.1），在该版本中引入了对方法参数校验、校验器依赖注入等特性的支持；在Java8发布后，Gunnar Morling于2013年又发布了JSR 380（Bean Validation 2.0），该版本中大量使用了Java8的新特性，如Optional、Lambda表达式、Type Annotation等。

目前被业界广泛使用的实现为Hibernate Validator框架。

# Java Bean Validation的基本用法

# Spring中应用Java Bean Validation

# 源码分析

# 参考文献

1. https://jcp.org/en/jsr/summary?id=Bean+Validation
2. https://beanvalidation.org/news/
3. https://hibernate.org/validator/
4. https://www.baeldung.com/javax-validation