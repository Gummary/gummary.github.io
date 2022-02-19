---
title: "使用Github Action和阿里云容器镜像服务搭建CI系统"
slug: build-ci-system
date: 2022-02-19T15:22:15+08:00
draft: false
---

<!--more-->

# 引言

在公司写代码的流程是一般是先在本地开发，然后推送到远程代码仓库，然后使用发布工具构建+执行就可以实现**自动拉取代码->编译代码->将程序及编译环境打包成Docker镜像->拉取镜像->启动镜像运行程序**这个流程。刚接触这个系统的时候，对这个自动化的编译构建运行启动非常好奇，也想自己构建一个这样一个系统。这个周比较闲，就抽空了解了一下，实现了一个简易的系统，本文主要记录下搭建的过程。

# 一些基础知识

前言所述的自动打包发布流程正式名称是CI/CD，也即持续集成/持续交付（持续部署）。**持续集成**是指，同一个团队不同开发者开发时可以频繁地将对应用的修改集成到代码的主干，持续集成工具可以自动构建、自动运行测试，确保修改代码的正确性。**持续交付**是指在合并到主干后，将代码交付给测试人员或用户，供他们部署到类生产环境中进行测试，如果测试通过，则手动部署到生产环境中。最后**持续部署**是持续交付的延伸，将最后手动部署的步骤也自动化。

# 实操环节

在公司内，CI/CD流程的主要流程是，开发者开发完代码后发布到代码仓库，然后触发CI/CD流程，Jenkins会自动拉取代码，构建后打包成一个容器镜像，然后拉取该镜像，发布到K8S集群上。本文借助Github实现代码管理，Github Action实现自动构建容器镜像，阿里容器镜像管理服务实现一个简单的持续集成系统。

## 应用代码管理与发布

本文使用的例子程序是一个简单的Java生产者消费者应用，分别包含生产者应用和消费者应用，二者通过消息队列实现通信。这里不展开叙述应用的具体实现，主要关注两个应用的打包发布流程。

这两个应用均由Maven管理，放在同一个Module下，共同依赖DemoApi，代码结构如下图所示。其中`setup/docker/*Dockerfile`为实现构建的dockerfile。

```
Demo/
├─ Producer/
│  ├─ pom.xml
│  ├─ src/
├─ Consumer/
│  ├─ pom.xml
│  ├─ src/
├─ DemApi/
│  ├─ src/
│  ├─ pom.xml
├─ setup/
│  ├─ docker/
│  │  ├─ ProducerDockerfile
│  │  ├─ ConsumerDockerfile
├─ pom.xml
```

我们先来看一下实现构建的Dockerfile，这里以ProducerDockerfile为例：

```dockerfile
#
# 构建阶段
#
FROM maven:3.6.0-jdk-11-slim AS build # 1

WORKDIR /home/app/ 	# 2
COPY Consumer/src Consumer/pom.xml /home/app/Consumer/ 
COPY Producer/src Producer/pom.xml /home/app/Producer/
COPY DemoApi/src DemoApi/pom.xml /home/app/DemoApi/
COPY pom.xml /home/app/pom.xml

RUN mvn -pl Producer -am -f /home/app/pom.xml clean package # 3

#
# 打包阶段
#
FROM openjdk:11-jre-slim # 4
COPY --from=build /home/app/Producer/target/Producer-1.0-SNAPSHOT-jar-with-dependencies.jar /usr/local/lib/producer.jar
ENTRYPOINT ["java","-jar","/usr/local/lib/producer.jar"] 
```

1. 首先制定构建镜像，这个应用使用Maven管理，所以使用基于maven的docker镜像
2. 指定构建的根目录并将需要的代码都拷贝到根目录中
3. 执行构建命令，这里只构建Producer这个应用
4. 这里使用了Docker的[mult-stage build](https://docs.docker.com/develop/develop-images/multistage-build/)，可以在一个Dockerfile中使用多个镜像。这里使用了两个镜像，在第一个镜像中构建，将构建的结果保存在第二个镜像中。这样做的好处是可以减少docker image的体积。

在本地，我们可以在根目录执行`docker build -t kafka.producer:latest -f ./setup/docker/Producer`实现该镜像的构建，构建完成后运行该docker即可。这里注意，在build时的根目录为当前目录，而不是Dockerfile所在的目录，所以Dockerfile内COPY的参数是相对build执行所在的目录。

## 使用阿里云容器镜像管理

在实现本地构建后，我们需要将容器镜像发布到一个Registry，供交付工具拉取镜像。常用的Docker Registry包括Docker Hub、GitHub Packages、阿里容器镜像服务、腾讯云容器镜像服务等，由于网络环境问题，这里采用阿里云容器镜像管理服务作为Docker Registry。

首先在阿里云容器镜像服务的实例列表中创建个人实例：

{{< tfigure src="images/2022-02-19-17-17-45.png" title="" width="" class="align-center">}}

然后创建一个命名空间，在命名空间中创建镜像仓库，最后设置访问阿里云镜像管理服务的账号密码：

{{< tfigure src="images/2022-02-19-17-20-14.png" title="" width="" class="align-center">}}

这里解释下命名空间、镜像仓库之间的关系。在pull一个镜像时，一个镜像的地址可能是：

```
registry.cn-shenzhen.aliyuncs.com/gum/kafka.producer:latest
```

该地址由`registry/namespace/image:tag`组成。其中registry用于存储和分发所有的docker镜像，namespace可以用于区分不同环境下的容器镜像，image为实际的镜像名称，tag用于标识同一镜像的多个版本。而之前提到的镜像仓库则是挂在命名空间下，一个镜像仓库只存储一种镜像的多种版本。

我们看下在本地如何推送打包好的镜像：

```bash
# 登录到阿里云镜像仓库
$ docker login --username=用户名 registry.cn-hangzhou.aliyuncs.com
# 给生成的镜像打标签，这里必须加上阿里云registry的地址，否则无法推送镜像
$ docker tag kafka.producer registry.cn-hangzhou.aliyuncs.com/gum/kafka.producer:latest
# 推送镜像
$ docker push registry.cn-hangzhou.aliyuncs.com/gum/kafka.producer:latest
```

## 使用GitHub Action

上述的两个动作都是通过手动执行命令实现的，下面我们通过Github Action实现开发完代码后自动构建镜像并推送。使用Github Action有两种实现方式：

1. 构建Github Action Steps实现编译，然后用构建的可执行文件创建一个新的镜像，将新镜像推送到Registry。也即将上述的Dockerfile的内容拆解到Github Action Steps。
2. 在容器内构建，将构建好的镜像推送到Registry。也即组合上述两个步骤。

下面给出第二个方法的yml文件：

```yaml
# This is a basic workflow to help you get started with Actions

name: CI

# 在push和pr合并到master时触发
on:
  push:
    branches: [ master ]
  pull_request:
    branches: [ master ]
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v1
			
			# 这里登录到阿里Registry
      - name: Login to DockerHub
        uses: docker/login-action@v1
        with:
          registry: ${{ secrets.ALI_DOCKER_HUB_REGISTRY }}
          username: ${{ secrets.ALI_DOCKER_HUB_USN }}
          password: ${{ secrets.ALI_DOCKER_HUB_PWD }}
			
			# 构建Producer的镜像并推送
      - name: Build Producer and Push
        uses: docker/build-push-action@v2
        with:
          context: .
          file: ./setup/docker/Producer
          push: true
          tags: registry.cn-hangzhou.aliyuncs.com/gum/kafka.producer:latest

			# 构建Consumer的镜像并推送
      - name: Build Consumer and Push
        uses: docker/build-push-action@v2
        with:
          context: .
          file: ./setup/docker/Consumer
          push: true
          tags: registry.cn-hangzhou.aliyuncs.com/gum/kafka.consumer:latest

```

在构建镜像并推送时，with下的内容就是前面命令行构建的拆解。


# 参考

1. [什么是 CI/CD？一文带你理解CI持续集成和CD持续交付/部署 - 红帽](https://www.redhat.com/zh/topics/devops/what-is-ci-cd)
2. [The Product Managers' Guide to Continuous Delivery and DevOps - Mind the Product](https://www.mindtheproduct.com/what-the-hell-are-ci-cd-and-devops-a-cheatsheet-for-the-rest-of-us/)
3. [About registries, repositories, images, and artifacts - Azure Container Registry | Microsoft Docs](https://docs.microsoft.com/en-us/azure/container-registry/container-registry-concepts)
3. [GitHub Actions持续集成阿里云容器镜像服务（ACR） - Mincong Huang](https://mincong.io/cn/github-actions-acr/)
3. [Docker: adding a file from a parent directory - Stack Overflow](https://stackoverflow.com/questions/24537340/docker-adding-a-file-from-a-parent-directory)
3. [How to build an optimal Docker image for your application? - Event-Driven.io](https://event-driven.io/en/how_to_buid_an_optimal_docker_image_for_your_application/)
3. [Build and push Docker images · Actions · GitHub Marketplace · GitHub](https://github.com/marketplace/actions/build-and-push-docker-images#git-context)
3. [How to set correct working-directory for Docker building and publishing in GitHub action? - Stack Overflow](https://stackoverflow.com/questions/63786311/how-to-set-correct-working-directory-for-docker-building-and-publishing-in-githu)
3. [Use multi-stage builds | Docker Documentation](https://docs.docker.com/develop/develop-images/multistage-build/)
3. [java - How to dockerize maven project? and how many ways to accomplish it? - Stack Overflow](https://stackoverflow.com/questions/27767264/how-to-dockerize-maven-project-and-how-many-ways-to-accomplish-it)
3. [两种github action 打包.Net Core 项目docker镜像推送到阿里云镜像仓库 - 九两白菜粥 - 博客园](https://www.cnblogs.com/jiuliangbaicaizhou/p/15224138.html)