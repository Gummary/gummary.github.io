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

## 反转链表

```python
class Solution:
    def reverseList(self, head: ListNode) -> ListNode:
        if not head: return None
        p, new_head = head, None
        while p:
            tmp = p.next
            p.next = new_head
            new_head = p
            p = tmp
        return new_head
```

## 复杂链表的复制

我需要在遍历到某一个node的时候，知道他的random是什么，是否创建了
1. 没创建就创建
2. 创建了则直接指向该节点

那么我怎么能立刻知道创建呢？直接能想到的办法就是使用字典，立刻就能知道是否创建过。由于obj的值不唯一，因此这个字典的key是原node，value是新node。判断random的时候直接去字典里找即可。

另一种不适用字典的方法是，将新创建的节点添加到原节点的后面。这样得到原来两倍长度的一个链表，这时候找新的random时，只需要找原节点的next节点即可。

```python
class Solution:
    def copyRandomList(self, head: 'Node') -> 'Node':
        if not head:
            return None
        cur = head
        while cur:
            node = Node(cur.val)
            node.next = cur.next
            cur.next = node
            cur = node.next
        cur = head
        while cur:
            if cur.random:
                cur.next.random = cur.random.next
            cur = cur.next.next
        
        result = head.next
        p1, p2 = head, result
        while p1 and p2.next:
            p1.next = p2.next
            p2.next = p2.next.next
            p1 = p1.next
            p2 = p2.next
        p1.next = None
        return result
```

# Day Three

## 替换空格

```python
class Solution:
    def replaceSpace(self, s: str) -> str:
        result = []
        for c in s:
            if c == ' ':
                result.append('%20')
            else:
                result.append(c)
        return ''.join(result)
```

## 

```python
class Solution:
    def reverseLeftWords(self, s: str, n: int) -> str:
        if n % len(s) == 0 or len(s) == 0:
            return
        n = n % len(s)
        return s[n:] + s[:n]
```

# Day Four

## 

```python
class Solution:
    def findRepeatNumber(self, nums: List[int]) -> int:
        if not nums:
            return
        i = 0
        while True:
            n = nums[i]
            if i == n:
                i += 1
                continue
            if nums[n] == n:
                return n
            nums[n], nums[i] = n, nums[n]
```

## 

这个题的本质是求出target的左边界和右边界，然后相减得到长度。

一种方法可以两次二分查找，分别找左边界和右边界。

另一种方式是，找到target之后，顺序遍历找到左右边界相减即可。

```python
class Solution:
    def search(self, nums: List[int], target: int) -> int:
        # 二分查找
        l, r, mid = 0, len(nums), -1
        while l < r:
            mid = (l + r) // 2
            if nums[mid] == target:
                break
            elif nums[mid] > target:
                r = mid
            else:
                l = mid+1
        if l >= r:
            return 0
        l, r = mid, mid
        # 左边界
        while l >= 0 and nums[l] == target:
            l -= 1
        while r < len(nums) and nums[r] == target:
            r += 1
        return r - l -1
```

## 

有序搜索先往二分上靠。

```python
class Solution:
    def missingNumber(self, nums: List[int]) -> int:
        l, r = 0, len(nums)
        while l < r:
            mid = (l+r) // 2
            if nums[mid] == mid:
                l = mid+1
            else:
                r = mid
        return r
```

# Reference

1. https://leetcode-cn.com/study-plan/lcof/?progress=ixaa2is
