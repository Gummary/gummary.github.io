---
title: Leetcode中的二分查找
date: 2020-07-20 11:04:24
tags:
summary: Leetcode上的二分查找题目及其变种解法
draft: true
---

<!-- more -->

二分查找是一个非常经典的查找算法，在有序数组中的时间复杂度为$O(logn)$。二分查找有很多变体，主要是在查找条件、判断条件及左右边界的处理上。下面将根据二分查找的主要三种变体介绍二分查找：

1. 标准二分查找
2. 二分查找查找左边界
3. 二分查找查找有边界
   

## 标准二分查找

~~~python
def binary_search(nums, target):
    l, r = 0, len(nums)-1
    while l <= r:
        mid = l + ((r-l) >> 1)
        if nums[mid] == target:
            return mid
        elif nums[mid] > target:
            r = mid - 1
        else:
            l = mid + 1
        return -1
~~~

- 循环跳出条件：`l > r` 或 `nums[mid] == target`
- 左右边界初始值分别为：`0,len(nums)-1`
- 左边界更新：`l = mid + 1`
- 有边界更新: `r = mid - 1`

这里的右边界是查找数组的最后一个元素，该元素也有可能是目标值.

当查找数组为奇数时，mid的位置位于中间；为偶数时，mid的位置为中间偏左的元素。

## 二分查找查找左边界

**对于数组有序,包含重复元素或数组部分有序,不包含重复元素的情况:**

~~~python
def binary_search(nums, target):
    l, r = 0, len(nums)-1
    while l < r:
        mid = l + ((r-l) >> 1)
        if nums[mid] < target:
            l = mid+1
        else:
            r = mid
    return l

~~~

- 循环跳出条件：`l >= r`
- 左右边界初始值分别为：`0,len(nums)-1`
- 左边界更新：`l = mid+1`
- 有边界更新: `r = mid`

与标准的二分查找不同之处在于,循环跳出条件和更新方式.

因为要查找左边界，可能存在重复数字，因此target与num[mid]相等也不代表找到了目标，所以在相等或大于的情况要将右边界向左收缩。

由于mid的位置总是中间或者偏左，因此在左右边界相遇时，l,r,mid只有一下两种可能：

1. l/r/mid在同一位置
2. l/mid在同一位置，r在l+1

在第二种情况中，下一次循环必定变为第一种情况，如果跳出条件为`l<=r`则会进入死循环，所以循环跳出条件为`l<r`

**数组部分有序,包含重复元素的情况:**

此时，不能将右边界直接更新为mid，会导致某些情况遗漏，如：

~~~python
[1,1,1,0,1,1]
~~~

若`r=mid`则会使查找范围略过目标位置。

在这种情况下二分查找为：

~~~python
def binary_search(nums, target):
    l, r = 0, len(nums)-1
    while l < r:
        mid = l + ((r-l) >> 1)
        if nums[mid] < target:
            l = mid+1
        else:
            r -= 1
    return l
~~~

右边界的更新变为`r=r-1`


## 二分查找查找右边界

查找右边界的方式与左边界基本相同：

~~~python
def binary_search(nums, target):
    l, r = 0, len(nums)-1
    while l < r:
        mid = l + ((r-l) >> 1) + 1
        if nums[mid] > target:
            r = mid - 1
        else:
            l = mid
    return r
~~~


唯一一点不同之处在于mid的计算方式，之前说过mid总是偏向左边界，因此为了让其偏向右边界，要将mid+1