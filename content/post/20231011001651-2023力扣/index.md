---
title: "2023力扣"
slug: 2023力扣
date: 2023-10-11T00:16:52+08:00
draft: true
---

<!--more-->

# 387. First Unique Character in a String

python中使用ord函数返回字符的ASCII值或Unicode值

```python
class Solution(object):
    def firstUniqChar(self, s):
        d = [0]*26
        for c in s:
            d[ord(c)-ord('a')] += 1
        for i, c in enumerate(s):
            if d[ord(c)-ord('a')] == 1:
                return i
        return -1
```
