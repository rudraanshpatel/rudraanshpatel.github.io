---
date: 2026-10-21
platform: LeetCode
id: "1"
title: Two Sum
link: /1
difficulty: Easy
tags:
  - array
  - hashing
time: O(n)
space: O(n)
---
## Problem

Given an array of integers and  target, return the indices of the two numbers that add up to the target. Exactly one valid pair exists, and the same element can't be used twice.

## Approach

The brute force checks every pair in O(n²). The faster way: for each number `x`, the partner it needs is `target - x`. Keep a hash map from value to index for the numbers already seen. If the partner is already in the map, that's the answer. Otherwise store `x` and move on. Checking before inserting means an element can never pair with itself, and one pass is enough because the second number of the pair always finds the first.

## Solution

```cpp
vector<int> twoSum(vector<int>& nums, int target) {
    unordered_map<int, int> seen;  // value -> index

    for (int i = 0; i < nums.size(); i++) {
        int need = target - nums[i];
        if (seen.count(need)) return {seen[need], i};
        seen[nums[i]] = i;
    }
    return {};
}
```