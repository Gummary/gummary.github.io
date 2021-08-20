---
title: 贪心算法题汇编
date: 2020-08-01 22:18:22
tags:
mathjax: true
draft: true
---

# 贪心算法介绍

>贪心算法（英語：greedy algorithm），又称贪婪算法，是一种在每一步选择中都采取在当前状态下最好或最优（即最有利）的选择，从而希望导致结果是最好或最优的算法。比如在旅行推销员问题中，如果旅行员每次都选择最近的城市，那这就是一种贪心算法。贪心算法在有最优子结构的问题中尤为有效。最优子结构的意思是局部最优解能决定全局最优解。简单地说，问题能够分解成子问题来解决，子问题的最优解能递推到最终问题的最优解。贪心算法与动态规划的不同在于它对每个子问题的解决方案都做出选择，不能回退。动态规划则会保存以前的运算结果，并根据以前的结果对当前进行选择，有回退功能。贪心法可以解决一些最优化问题，如：求图中的最小生成树、求哈夫曼编码……对于其他问题，贪心法一般不能得到我们所要求的答案。一旦一个问题可以通过贪心法来解决，那么贪心法一般是解决这个问题的最好办法。由于贪心法的高效性以及其所求得的答案比较接近最优结果，贪心法也可以用作辅助算法或者直接解决一些要求结果不特别精确的问题。

以上摘自维基百科，但是这些概念性的知识并不能帮助我们选择解决实际的问题，而实践是认识的基础、认识的来源、认识发展的动力，因此本文选一些代表性的问题及解法，尽可能的说明白贪心算法在每个问题中的应用。

<!-- more -->

# 背包相关问题

## 最优装载

**题目出处**

算法竞赛入门经典，p231

**题目描述**

给定n个物体，第i个物体的重量为$w_i$，选择尽量多的物体，使总重量不超过C。

**题目分析**

由于要尽可能多的拿物体，因此优先选择重量轻的物体。

~~~python
def solution(weights, v):
    weights = sorted(weights)
    count = 0
    for w in weights:
        if v > w:
            v -= w
            count += 1
    return count
~~~

## 部分背包问题

**题目出处**

算法竞赛入门经典，p231

**题目描述**

给定C个物体，其重量为$w_i$,价值为$c_i$,背包容量为$v$,每个物体都能拿全部或者部分，那么如何拿物品，使背包的总价值最大。

**题目分析**

引入价值之后就不能每次只拿最轻的，因为可能最轻的价值也是最低的，这种情况下需要根据价值与重量的比值进行排序，每次选择价值最高重量最低的物品。由于可以拿部分物品，拿最后一个物体一般是拿部分。

~~~python
from typing import List

def solution(w:List, c:List, v:int)->List:
    result = [0] * len(v)
    wc = ((i, ww, cc) for i, ww, cc in enumerate(zip(w, c)))
    wc = sorted(wc, key=lambda x:x[2]/x[1])
    for i, ww, cc in wc:
        if v > cc:
            result[i] = cc
            v -= cc
        else:
            result[i] = v
            break

    return result
~~~

## 乘船问题

**题目出处**

算法竞赛入门经典，p231

**题目描述**

共有n个人，每个人的重量为$w_i$，每艘船最多装两个人且重量为C。

**题目分析**

考虑最轻的人，如果最轻的人不能和其他人同乘坐一条船，那么所有人都只能乘一条船，因为任意两个人都不能乘同一条船。

如果最轻的人可以和其他人乘同一条船，那么选择与他一起乘船的人中，最终的那一个，这里用到了贪心的做法，使得每艘船浪费的空间最小。

~~~python
def solution(w: List, C:int)->int:
    w = sorted(w)
    i, j, end = 0, len(w)-1, len(w)
    result = 0
    while i < j:
        while i < j and w[i] + w[j] > C:
            j-=1
        result += end - j
        end = j
        i+=1

    return result
~~~

# 区间相关问题

## 求重叠区间的最大数量

**题目出处**

猿辅导笔试

**题目描述**

给定一些区间`[start, end]`，求重叠区间的最大数量

**题目分析**

首先对区间进行排序，先根据起始点排序，若起始点相同则根据终点排序。遍历排序号的区间，用一个最小堆保存当前区间的最小终点。

每次遍历比较最小end与当前区间的起点，

- 如果起点比最小end小，说明与堆中所有的区间都有交集，入堆
- 如果起点比最小end大，说明与最小end所在的区间没有交集，可以把当前区间与最小end的区间合并，也即从堆中取出最小end，将当前end加入。可以合并的原因是：
  - 区间已经排好序了，所以之后不可能有区间位于二者之间
  - 这两个区间与堆中的其他区间都重叠，没有增加最大重叠的数量

~~~python
def solution(intervals: List[Tuple]) -> int:
    intervals = sorted(intervals)
    heap = []
    heap.append(intervals[0][1])
    for i, seg in enumerate(intervals[1:]):
        if heap[0] <= seg[0]:
            heappop(heap)
        heappush(heap, seg[1])
    return len(intervals)
~~~

## 求非重叠区间的最大数量

**题目出处**

[Leetcode453](https://leetcode.com/problems/non-overlapping-intervals/)

**题目描述**

给定一些区间，求需要移除区间的最小数量，使区间之间不重叠。

**题目分析**

对区间按照终点进行排序，从最小的重点开始，移除与最小终点重叠的区间，若不冲突则更新最小终点。

这里应用贪心思想的位置在于，尽可能选择终点较小的区间，贪心有效的点在于：

1. 选择end较小的点，如果发生冲突了，那么因为end较小，所以会有更多的时间选择其他区间。

~~~python
class Solution:
    def eraseOverlapIntervals(self, intervals: List[List[int]]) -> int:
        if intervals == []:
            return 0
        intervals = sorted(intervals, key=lambda x:x[1])
        current_min = intervals[0][1]
        result = 0
        for interval in intervals[1:]:
            if interval[0] < current_min:
                result += 1
            else:
                current_min = interval[1]
        return result
~~~        

