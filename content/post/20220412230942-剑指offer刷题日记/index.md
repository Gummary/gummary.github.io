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

## 左旋转字符串

```python
class Solution:
    def reverseLeftWords(self, s: str, n: int) -> str:
        if n % len(s) == 0 or len(s) == 0:
            return
        n = n % len(s)
        return s[n:] + s[:n]
```

# Day Four

## 数组中重复的数字

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

## 数组中重复的数字

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

## 0～n-1中缺失的数字

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

# Day Five

## 二维数组中的查找

```python
class Solution:
    def findNumberIn2DArray(self, matrix: List[List[int]], target: int) -> bool:
        if not matrix: return False
        end = len(matrix[0])
        for i in range(len(matrix)):
            possiable_array = matrix[i]
            if end == 0: return False
            l, r = 0, end
            while l < r:
                mid = (l+r) // 2
                if possiable_array[mid] == target:
                    return True
                elif possiable_array[mid] > target:
                    r = mid
                else:
                    l = mid + 1
            end = l
        return False
```

一种更简单的解法是，将矩阵向左旋转45°，然后可以将其看作二叉树，左边节点比中间的数值小，右边的比中间的大，因此可转换为二叉查找树的搜索。

```python
class Solution:
    def findNumberIn2DArray(self, matrix: List[List[int]], target: int) -> bool:
        if not matrix: return False
        i, j = 0, len(matrix[0])-1
        while i < len(matrix) and j >= 0:
            if matrix[i][j] > target:
                j -= 1
            elif matrix[i][j] < target:
                i += 1
            else:
                return True

        return False
```

## 旋转数组的最小数字

很有意思的一道题。这个题的输入是一个含重复元素的有序数组，我们先降低一下难度，看下如果没有重复元素我们怎么解。

**没有重复元素**

如果没有重复元素，那输入就是一个有旋转的有序数组，在有序数组中查找元素，我们首先就应该往二分查找上靠。而二分查找的关键在于，比较中间元素与目标元素的大小，然后让区间逼近目标元素。

在本题中，我们要找的是最小值，让区间逼近这个最小值，那么我们的中间元素应该和谁比呢？既然我们是用区间逼近，最后取值是区间位置的值，那么我们可以让中间元素和区间两端的值比较。在本题中只能与右区间比较（原因下面解释）。

当数组旋转后，我们可以利用旋转数组的性质来移动区间：

- 当中间值比右区间端点值大时，说明mid在最小值的左侧
- 当中间值比右区间端点值大时，说明mid在最小值的右侧或mid为最小值
  
有了这个判断后，我们很容易写出如下代码：

```python
class Solution:
    def minArray(self, numbers: List[int]) -> int:
        l, r = 0, len(numbers)-1
        while l <= r:
            mid = (l+r) // 2
            if numbers[mid] > numbers[r]: l = mid + 1
            elif numbers[mid] < numbers[r]: r = mid    # mid可能为最小值
            else: break
        return numbers[r]
```

我们再来看下为什么不能和左区间比较？如果和左端点比较，则移动区间的方法与右端点相反，这里不再赘述。下面考虑一个反例，如果数组没有旋转，那么array[l]为最小值，array[mid] > array[l]，但我们认为最小值位于mid的右侧，会让l=mid+1，丢失最小值，所以只能与右端点比较。

**有重复元素**

我们再来看下有重复元素如何处理。有重复元素时我们额外需要考虑mid和右端点相等的情况下怎么处理，如果二者相等，则有两种情况：

1. 右端点与中间值相同，均为最小值
2. 最小值在二者之间

所以我们不能让r=mid，我们要让右端点移动的更为谨慎：r -= 1.

另外在有重复值后，最终最小值也不再是右端点了。因为随着r的不断减小，mid会不断趋近于l，最终等于l，那么当l=r时，r会继续向左移动，最终最小值会在l的位置上。所以最终代码为：

```python
class Solution:
    def minArray(self, numbers: List[int]) -> int:
        l, r = 0, len(numbers)-1
        while l <= r:
            mid = (l+r) // 2
            if numbers[mid] > numbers[r]: l = mid + 1
            elif numbers[mid] < numbers[r]: r = mid
            else: r -= 1
        return numbers[l]
```

## 第一个只出现一次的字符

```python
class Solution:
    def minArray(self, numbers: List[int]) -> int:
        l, r = 0, len(numbers)-1
        while l <= r:
            mid = (l+r) // 2
            if numbers[mid] > numbers[r]: l = mid + 1
            elif numbers[mid] < numbers[r]: r = mid
            else: r -= 1
        return numbers[l]
```

# Day Six

## 从上到下打印二叉树 I

```python
class Solution:
    def levelOrder(self, root: TreeNode) -> List[int]:
        if not root: return []
        result, q = [], [root]
        while q:
            node = q.pop(0)
            if node.left: q.append(node.left)
            if node.right: q.append(node.right)
            result.append(node.val)
        return result
```

## 从上到下打印二叉树 II

```python
class Solution:
    def levelOrder(self, root: TreeNode) -> List[List[int]]:
        if not root: return []
        result, q = [], [root]
        while q:
            tmp = []
            result.append([n.val for n in q])
            for n in q:
                if n.left: tmp.append(n.left)
                if n.right: tmp.append(n.right)
            q = tmp
        return result
```

## 从上到下打印二叉树 III

```python
class Solution:
    def levelOrder(self, root: TreeNode) -> List[List[int]]:
        if not root: return []
        result, q, reverse = [], [root], False
        while q:
            tmp = []
            if reverse: q = q[::-1]
            result.append([n.val for n in q])
            if reverse: q = q[::-1]
            for n in q:
                if n.left: tmp.append(n.left)
                if n.right: tmp.append(n.right)
            q = tmp
            reverse = not reverse
        return result
```

# Day Seven

## 树的子结构

```python
class Solution:
    def isSubStructure(self, A: TreeNode, B: TreeNode) -> bool:
        if not A or not B:
            return False

        def helper(A, B):
            if not B:
                return True
            if not A or A.val != B.val:
                return False
            return helper(A.left, B.left) and helper(A.right, B.right)

        return helper(A, B) or self.isSubStructure(A.left, B) or self.isSubStructure(A.right, B)
```

## 二叉树的镜像

```python
class Solution:
    def mirrorTree(self, root: TreeNode) -> TreeNode:
        if not root: return root
        root.left, root.right = root.right, root.left
        root.left = self.mirrorTree(root.left)
        root.right = self.mirrorTree(root.right)
        return root
```

## 对称的二叉树

```python
class Solution:
    def isSymmetric(self, root: TreeNode) -> bool:
        if not root:
            return True
    
        def helper(l, r):
            if not l and not r:
                return True
            if not l or not r or l.val != r.val: return False
            return helper(l.left, r.right) and helper(l.right, r.left)

        return helper(root.left, root.right)
```

# Reference

1. https://leetcode-cn.com/study-plan/lcof/?progress=ixaa2is
