---
title: "JAVA网络编程"
slug: JAVA网络编程
date: 2022-03-22T19:32:15+08:00
draft: true
---

<!--more-->

# ByteBuffer

ByteBuffer的内部结构是一个数组及三个位置标识组成。三个位置标识分别为position、limit和capacity。

- position，用于指定当前读出/写入的初始位置
- limit，制定读出/写入的停止位置
- capacity，内部数组的大小

在从ByteBuffer中读出数据或向其中写入数据时，需要结合ByteBuffer提供的API，调整三个位置标识的值。常用的方法包括：

- clear，将position置为0，limit设置为capacity，丢弃mark的位置。通常在向ByteBuffer中写入时调用。
- flip，将limit设置为当前的position，将position的设置为0，通常在从ByteBuffer中读取时调用。
- rewind，讲position设置为0，通常用于重新读取数据时使用。