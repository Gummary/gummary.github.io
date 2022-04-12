---
title: "剑指offer刷题日记"
slug: 剑指offer刷题日记
date: 2022-04-12T23:09:45+08:00
draft: true
---

<!--more-->

# Day One

## 用两个栈实现队列

```python
class CQueue:
    def __init__(self):
        self.s1, self.s2 = [], []

    def appendTail(self, value: int) -> None:
        self.s1.append(value)

    def deleteHead(self) -> int:
        if self.s2: return self.s2.pop()
        if not self.s1: return -1
        while len(self.s1) > 0:
            self.s2.append(self.s1.pop())
        return self.s2.pop()
```

## 包含min函数的栈

首先想到，只用栈这个结构肯定没办法实现这个功能，那么用空间换时间，用另一个数组来表示当前的最小值


```python
class MinStack:

    def __init__(self):
        """
        initialize your data structure here.
        """
        self.min_stack = []
        self.stack = []

    def push(self, x: int) -> None:
        self.stack.append(x)
        if not self.min_stack:
            self.min_stack.append(x)
        elif x <= self.min_stack[-1]:
            self.min_stack.append(x)
        else:
            self.min_stack.append(self.min_stack[-1])

    def pop(self) -> None:
        if not self.stack:
            return
        self.stack.pop()
        self.min_stack.pop()

    def top(self) -> int:
        if not self.stack:
            return None
        return self.stack[-1]

    def min(self) -> int:
        if not self.min_stack:
            return None
        return self.min_stack[-1]
```

一个小的优化点是，在辅助栈中，我们可以只存一次最小值。距离来说如果栈的第一个元素最小，那么在辅助栈中，所有的元素均为栈的第一个元素。这是完全没必要的，我们只需要在出栈的时候比较出栈元素是否是当前最小的即可。如果是最小的，那么两个栈一起出，否则只出一个即可。

```python
class MinStack:

    def __init__(self):
        """
        initialize your data structure here.
        """
        self.min_stack = []
        self.stack = []


    def push(self, x: int) -> None:
        self.stack.append(x)
        if not self.min_stack or x <= self.min_stack[-1]:
            self.min_stack.append(x)

    def pop(self) -> None:
        if not self.stack:
            return
        if self.stack.pop() == self.min_stack[-1]:
            self.min_stack.pop()

    def top(self) -> int:
        if not self.stack:
            return None
        return self.stack[-1]


    def min(self) -> int:
        if not self.min_stack:
            return None
        return self.min_stack[-1]
```

# Day Two

## 从尾到头打印链表

```python
class Solution:
    def reversePrint(self, head: ListNode) -> List[int]:
        if not head: return []
        result = []
        l = 0
        p = head
        while p:
            l += 1
            p = p.next
        result = [0] * l
        while head:
            result[l-1] = head.val
            l -= 1
            head = head.next
        return result
```

# Reference

1. https://leetcode-cn.com/study-plan/lcof/?progress=ixaa2is
