---
title: "Java Bean Validation with Spring Boot"
slug: java-bean-validation-with-spring-boot
date: 2023-01-30T11:08:53+08:00
draft: false
categories: ["spring"]
tags: ["Java", "Spring"]
---

在应用程序中，为了确保程序运行正确，通常需要对用户输入进行校验。Java中为了对Bean进行校验先后发布了JSR 303、JSR 349、JSR 380，帮助Java开发者快速校验Java Bean。作为Java应用开发中的主流框架Spring，也大量使用了Java Bean Validation。本文先简单介绍Java Bean Validation的发展历史，然后介绍在Spring中如何应用，最后介绍Spring中Bean Validation的实现原理。

<!--more-->

# Java Bean Validation发展历史

Emmanuel Bernard在2009年发布了JSR 303（Bean Validation 1.0），在该标准中定义了如何使用注解对JavaBean进行校验；Emmanuel于2013年又发布了JSR 349（Bean Validation 1.1），在该版本中引入了对方法参数校验、校验器依赖注入等特性的支持；在Java8发布后，Gunnar Morling于201年又发布了JSR 380（Bean Validation 2.0），该版本中大量使用了Java8的新特性，如Optional、Lambda表达式、Type Annotation等。

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

1. 对于HTTP GET等请求，通常使用@RequestParam、@PathVariable注解接收请求参数及URL中的参数；
2. 对于HTTP POST请求，通常是用@RequestBody注解接受请求体。

下面看下如何对GET、POST请求进行参数校验。

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

GET请求中，如果参数数量较少，可以使用简单类型并使用@RequestParam注解接收参数，然后给需要校验的参数加校验注解；如果参数数量过多，可以将参数聚合到一个类中，然后给该类的参数添加@Valid注解。无论是使用简单类型还是类来接收参数，都**必须**在Contoller类上加@Validated注解。

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

对于POST请求，后端通常用@RequestBody并使用一个类来接受请求体的内容，在类中添加校验项后，只需要在参数上加@Valid或@Validated注解即可。

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

如果javax.validation.constraints中的校验器不满足校验要求，还可以自定义一个校验注解和校验器。

例如我们给UserVO增加一个身份证属性并对其进行校验。首先定义校验注解，定义的注解中必须包含以下内容：

1. message，当校验不通过时的提示信息，默认的信息从ValidationMessages.properties指定
2. groups，分组校验的组别
3. payload，用处较少
4. Constraint注解，指定校验器

```java
@Target({ElementType.FIELD})
@Retention(RetentionPolicy.RUNTIME)
@Constraint(validatedBy = IdCardNoValidator.class)
@Documented
public @interface IdCardNo {
    String message() default "{IdCardNo.invalid}";
    Class<?>[] groups() default {};
    Class<? extends Payload>[] payload() default {};
}
```

对应的校验类必须实现ConstraintValidator接口，接口的第一个范型为实际要校验的注解，第二个为校验的类型。

在isValid方法中进行实际的校验，第一个方法参数是要校验的对象，第二个是校验的上下文信息，可以使用该对象自定义错误信息(详见：[Validator校验器中重新定义默认的错误信息模板](https://blog.csdn.net/qq_38218238/article/details/81477915))。

```java
public class IdCardNoValidator implements ConstraintValidator<IdCardNo, String> {
 	@Override
    public boolean isValid(String value, ConstraintValidatorContext context) {
        return validateCard(value);
    }

    private boolean validateCard(String value) {
        // 略
    }
}
```

具体使用：

```java
@Data
@Builder
public class UserVO {
    // ...

    @IdCardNo(message = "身份证号格式错误")
    private String idCardNo;
}
```

## Service层进行校验

除了在Controller层对用户输入校验，还可以在Serivce层进行校验。校验方法是在接口方法及实现方法中给需校验的参数加@Valid注解，在实现类上加@Validated注解。

```java
public interface UserOperateService {
    void addUser(@Valid UserVO userVO);
}

@Slf4j
@Service
@Validated
public class UserOperateServiceImpl implements UserOperateService {

    @Override
    public void addUser(@Valid UserVO userVO) {
        log.info("[addUser] userVO: {}", JsonUtil.object2Json(userVO));
    }
}
```

## 显式校验

在没有Spring框架的情况下，如果也需要对参数进行校验，可以直接调用Hiberate的方法对参数进行校验。

```java
class ProgrammaticallyValidatingService {
  void validateInput(Input input) {
    ValidatorFactory factory = Validation.buildDefaultValidatorFactory();
    Validator validator = factory.getValidator();
    Set<ConstraintViolation<Input>> violations = validator.validate(input);
    if (!violations.isEmpty()) {
      throw new ConstraintViolationException(violations);
    }
  }
}
```

这种方式会在每次校验的时候创建一个ValidatorFactory和Validator，而参数校验的时候会获取校验类的所有远数据并缓存起来，提高下次校验时的校验速度。但是每次重新创建，该缓存会失效，所以对于频繁调用的方法，不建议使用这种方式进行校验。

而ValidatorFactory和Validator都是线程安全的，因此一个Application中只用一个ValidatorFactory单例即可。

# Spring参数校验源码分析

## 校验类加载

Spring Boot中加载校验类的配置类为ValidationAutoConfiguration，该类为容器中提供了两个类：

- LocalValidatorFactoryBean，当容器中不存在Validator时，作为默认的校验器。
- MethodValidationPostProcessor，是一个BeanPostProcessor，在应用中Bean初始化完成后，会判断Bean是否使用了@Validated注解，如果使用了则给该Bean的方法加上校验的切面。


```java
@AutoConfiguration
@ConditionalOnClass(ExecutableValidator.class)
@ConditionalOnResource(resources = "classpath:META-INF/services/javax.validation.spi.ValidationProvider")
@Import(PrimaryDefaultValidatorPostProcessor.class)
public class ValidationAutoConfiguration {

	@Bean
	@Role(BeanDefinition.ROLE_INFRASTRUCTURE)
	@ConditionalOnMissingBean(Validator.class)
	public static LocalValidatorFactoryBean defaultValidator(ApplicationContext applicationContext) {
		LocalValidatorFactoryBean factoryBean = new LocalValidatorFactoryBean();
		MessageInterpolatorFactory interpolatorFactory = new MessageInterpolatorFactory(applicationContext);
		factoryBean.setMessageInterpolator(interpolatorFactory.getObject());
		return factoryBean;
	}

	@Bean
	@ConditionalOnMissingBean(search = SearchStrategy.CURRENT)
	public static MethodValidationPostProcessor methodValidationPostProcessor(Environment environment,
			@Lazy Validator validator, ObjectProvider<MethodValidationExcludeFilter> excludeFilters) {
		FilteredMethodValidationPostProcessor processor = new FilteredMethodValidationPostProcessor(
				excludeFilters.orderedStream());
		boolean proxyTargetClass = environment.getProperty("spring.aop.proxy-target-class", Boolean.class, true);
		processor.setProxyTargetClass(proxyTargetClass);
		processor.setValidator(validator);
		return processor;
	}
}
```

### 校验切面

在ValidationAutoConfiguration中提供的MethodValidationPostProcessor的继承关系为：

{{< tfigure src="images/MethodValidationPostProcessor.png" title="" width="" class="align-center">}}


在MethodValidationPostProcessor中加载了一个DefaultPointcutAdvisor，包含的pointcut为AnnotationMatchingPointcut，关注的是有Validated注解的类；包含的advise为MethodValidationInterceptor，进行实际的参数校验。

MethodValidationInterceptor的校验部分：

```java
public Object invoke(MethodInvocation invocation) throws Throwable {
    // Avoid Validator invocation on FactoryBean.getObjectType/isSingleton
    if (isFactoryBeanMetadataMethod(invocation.getMethod())) {
        return invocation.proceed();
    }

    Class<?>[] groups = determineValidationGroups(invocation);

    // Standard Bean Validation 1.1 API
    ExecutableValidator execVal = this.validator.forExecutables();
    Method methodToValidate = invocation.getMethod();
    Set<ConstraintViolation<Object>> result;

    Object target = invocation.getThis();
    Assert.state(target != null, "Target must not be null");
    
    // 执行方法前检验参数
    try {
        result = execVal.validateParameters(target, methodToValidate, invocation.getArguments(), groups);
    }
    catch (IllegalArgumentException ex) {
        // Probably a generic type mismatch between interface and impl as reported in SPR-12237 / HV-1011
        // Let's try to find the bridged method on the implementation class...
        methodToValidate = BridgeMethodResolver.findBridgedMethod(
                ClassUtils.getMostSpecificMethod(invocation.getMethod(), target.getClass()));
        result = execVal.validateParameters(target, methodToValidate, invocation.getArguments(), groups);
    }
    if (!result.isEmpty()) {
    // 如果有校验不通过，则抛出ConstraintViolationException
        throw new ConstraintViolationException(result);
    }

    Object returnValue = invocation.proceed();
    // 调用结束后校验返回值
    result = execVal.validateReturnValue(target, methodToValidate, returnValue, groups);
    if (!result.isEmpty()) {
    // 如果有校验不通过，则抛出ConstraintViolationException
        throw new ConstraintViolationException(result);
    }

    return returnValue;
}
```


## POST参数校验

Spring处理Http请求时首先根据请求URL定位到要实际调用的方法，然后根据要调用的方法参数确定请求参数的解析类。

对于用RequestBody注解的参数，使用解析类为RequestResponseBodyMethodProcessor，在对参数解析完成后，会对参数进行校验。

```java
@Override
public Object resolveArgument(MethodParameter parameter, @Nullable ModelAndViewContainer mavContainer,
        NativeWebRequest webRequest, @Nullable WebDataBinderFactory binderFactory) throws Exception {

    parameter = parameter.nestedIfOptional();
    Object arg = readWithMessageConverters(webRequest, parameter, parameter.getNestedGenericParameterType());
    String name = Conventions.getVariableNameForParameter(parameter);

    if (binderFactory != null) {
        WebDataBinder binder = binderFactory.createBinder(webRequest, arg, name);
        if (arg != null) {
            // 校验参数
            validateIfApplicable(binder, parameter);
            if (binder.getBindingResult().hasErrors() && isBindExceptionRequired(binder, parameter)) {
                throw new MethodArgumentNotValidException(parameter, binder.getBindingResult());
            }
        }
        if (mavContainer != null) {
            mavContainer.addAttribute(BindingResult.MODEL_KEY_PREFIX + name, binder.getBindingResult());
        }
    }

    return adaptArgumentIfNecessary(arg, parameter);
}
```

## GET参数校验

对于GET参数的校验则不是在校验类中实现的，而是利用了Spring的AOP机制。所以对于GET请求的方法，其Controller类必须加@Validated注解。

具体代码见校验切面，这里不再赘述。

# 总结

本文主要介绍了Java Bean Validation的发展历史，在Spring中的应用及Spring中对Web参数校验的原理。

# 参考文献

1. [The Java Community Process(SM) Program - JSRs: Java Specification Requests - summary](https://jcp.org/en/jsr/summary?id=Bean+Validation)
2. [Jakarta Bean Validation - News](https://beanvalidation.org/news/)
3. [The Bean Validation reference implementation. - Hibernate Validator](https://hibernate.org/validator/)
4. [Java Bean Validation Basics](https://www.baeldung.com/javax-validation)
5. [java - Spring Validation最佳实践及其实现原理，参数校验没那么简单！ - 个人文章 - SegmentFault 思否](https://segmentfault.com/a/1190000023471742#item-1-3)
6. [Spring Method Parameter](https://docs.spring.io/spring-framework/docs/current/reference/html/integration.html#rest-http-interface-method-parameters)
7. [Hibernate Validator 8.0.0.Final - Jakarta Bean Validation Reference Implementation: Reference Guide](https://docs.jboss.org/hibernate/validator/8.0/reference/en-US/html_single/#chapter-bootstrapping)
