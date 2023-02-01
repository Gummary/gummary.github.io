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

{{< tfigure src="images/spring-validation-history.png" title="" width="" class="align-center">}}

Hibernate Validator是JSR 380的一个参考实现，被业界广泛使用，能够在展示层、业务层、数据层对输入进行校验。

{{< tfigure src="images/20230130142747.png" title="" width="" class="align-center">}}

# Spring中应用Java Bean Validation

在Spring也有对Java Bean Validation的封装，maven组件为：

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-validation</artifactId>
</dependency>
```

## Spring Controller参数校验

在使用Spring进行Web开发时，接收参数的方式有以下两种：

1. 对于HTTP Get等请求，通常使用@RequestParam、@PathVariable注解接收请求参数及URL中的参数；
2. 对于HTTP Post请求，通常是用@RequestBody注解接受请求体。

下面看下如何对Get、Post请求进行参数校验。

首先定义接受请求参数的类，并对类中的参数增加校验项：

```java
@Data
@Builder
public class UserVO {

    private Long id;

    @NotBlank(message = "名称不能为空")
    private String name;

    @Email(message = "邮箱格式错误")
    private String email;
}
```

get请求中，如果参数数量较少，可以使用简单类型并使用@RequestParam注解接收参数，然后给需要校验的参数加校验注解；如果参数数量过多，可以将参数聚合到一个类中，然后给该类的参数添加@Valid注解。无论是使用简单类型还是类来接收参数，如果需要校验参数，都**必须**在Contoller类上加@Validated注解。

```java
@Slf4j
@Validated
@RestController
public class UserQueryController {

    @GetMapping("/user/query/id")
    public UserVO queryUserById(@RequestParam @Min(5) int id) {
        log.info("[queryUserById] {}", id);
        return null;
    }

    @GetMapping("/user/query/full")
    public UserVO queryUser(@Valid UserVO userVo) throws JsonProcessingException {
        ObjectMapper objectMapper = new ObjectMapper();
        log.info("[queryUser] {}", objectMapper.writeValueAsString(userVo));

        return null;
    }
}
```

对于post请求，后端通常用@RequestBody并使用一个类来接受请求体的内容，在类中添加校验项后，只需要在参数上加@Valid或@Validated注解即可。

```java
@Slf4j
@RestController
public class UserOperateController {
    @PostMapping("/user/add")
    public UserVO addUser(@Valid @RequestBody UserVO userVO) {

        log.info("add user");
        return null;
    }
}
```

### 统一处理校验错误

当参数校验失败时，Spring会抛出异常，在不同场景下抛出的异常有所不同，具体区别如下：

| HTTP请求 | 参数注解     | 抛出异常类型                    | HTTP 返回状态码 |
| -------- | ------------ | ------------------------------- | --------------- |
| GET      | 无注解       | BindException                   | 400             |
| GET      | RequestParam | MethodArgumentNotValidException | 500             |
| GET      | PathVariable | MethodArgumentNotValidException | 500             |
| POST     | RequestBody  | ConstraintViolationException    | 400             |

如果想要返回统一的结构或针对校验失败返回统一的状态码，有两种方法。

如果只针对某一个Controller设置，则可以在该Controller中新增一个方法，处理抛出的异常，并返回400：

```java
@ExceptionHandler(ConstraintViolationException.class)
@ResponseStatus(HttpStatus.BAD_REQUEST)
ResponseEntity<String> handleConstraintViolationException(ConstraintViolationException e) {
    return new ResponseEntity<>("参数校验失败：" + e.getMessage(), HttpStatus.BAD_REQUEST);
}
```

如果想针对全局配置，则可以添加一个全局处理类，用@ControllerAdvice注解。下面的两个方法分别处理ConstraintViolationException和MethodArgumentNotValidException，并返回了一个统一的结构HttpResponse。

```java
public class HttpResponse<T> implements Serializable {
    private static final long serialVersionUID = -5831412260861490028L;
    private int status;
    private String msg;
    private T data;
}
```

```java
@ControllerAdvice
public class ValidateControllerAdvice {
    @ExceptionHandler(ConstraintViolationException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    @ResponseBody
    HttpResponse<?> onConstraintValidationException(ConstraintViolationException e) {
        // 获取错误
        String errorMsg = e.getConstraintViolations().stream().map(ConstraintViolation::getMessage).collect(Collectors.joining(" "));
        // 构造统一返回结果
        HttpResponse<?> response = new HttpResponse<>();
        response.setStatus(500);
        response.setData(null);
        response.setMsg(errorMsg);
        return response;
    }

    @ResponseBody
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    @ExceptionHandler(MethodArgumentNotValidException.class)
    HttpResponse<?> onConstraintViolationException(MethodArgumentNotValidException e) {
        // 获取错误
        String errorMsg = e.getBindingResult().getFieldErrors().stream()
                .map(DefaultMessageSourceResolvable::getDefaultMessage).collect(Collectors.joining(" "));
        // 构造统一返回结果
        HttpResponse<?> response = new HttpResponse<>();
        response.setStatus(500);
        response.setData(null);
        response.setMsg(errorMsg);
        return response;
    }
}
```

Controller中处理方法优先级比全局的处理类高。

## 自定义校验器

## 分组校验

## Service层进行校验

## 显式校验



# 源码分析

# 参考文献

1. https://jcp.org/en/jsr/summary?id=Bean+Validation
2. https://beanvalidation.org/news/
3. https://hibernate.org/validator/
4. https://www.baeldung.com/javax-validation
5. https://segmentfault.com/a/1190000023471742#item-1-3
6. https://docs.spring.io/spring-framework/docs/current/reference/html/integration.html#rest-http-interface-method-parameters
