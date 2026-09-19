Altina is collecting intervals. A pair of positive integers $[l, r]$ with $l < r$ is considered an interval, and the length of such an interval is defined as $r - l$.

An interval $[l, r]$ is said to contain another interval $[x, y]$ if and only if $l \le x$ and $y \le r$. Notably, every interval contains itself.

The **maximum common subinterval** of a non-empty set $S$ is defined as the longest interval that is contained within every interval in $S$. If no such interval exists, it is undefined.

The **minimum common superinterval** of a non-empty set $S$ is defined as the shortest interval that contains every interval in $S$. Note that such an interval always exists.

Initially, Altina's collection is empty. There will be $Q$ events that modify her collection.

1. Altina adds an interval $[l, r]$ to her collection. If $[l, r]$ already exists in her collection, it should be counted as a distinct interval.
2. Altina removes an interval $[l, r]$ from her collection. If there are multiple such intervals, only one is removed, ensuring her collection remains non-empty.

After each event, Altina selects a non-empty subset $S$ from her collection, subject to the following conditions:

- Among all possible selections, she chooses one where the maximum common subinterval is undefined. If no such selection exists, she chooses one with the smallest length of the maximum common subinterval.
- Among all subsets $S$ that satisfy the above condition, she chooses one with the smallest length of the minimum common superinterval.

For each event, output the length of the minimum common superinterval of the set $S$ that Altina would choose.

## Input Format

The first line contains a positive integer $Q$, representing the number of events.  
The next $Q$ lines describe each event, formatted as follows:

- `A l r`: Add an interval $[l, r]$ to Altina's collection.
- `R l r`: Remove an interval $[l, r]$ from Altina's collection, ensuring it exists and her collection remains non-empty.

## Output Format

Output $Q$ lines, each containing a positive integer representing the length of the minimum common superinterval of the set $S$ that Altina would choose after each event.

## Sample Input and Output

### Input Sample #1

```
5
A 1 5
A 2 7
A 4 6
A 6 8
R 4 6
```

### Output Sample #1

```
4
6
5
4
7
```

## Notes/Hints

### Sample Explanation

Adding $[1,5]$, choosing $[1,5]$ is optimal, answer is $4$.

Adding $[2,7]$, choosing $[1,5],[2,7]$ is optimal, answer is $7-1=6$.

Adding $[4,6]$, choosing $[1,5],[4,6]$ is optimal, answer is $6-1=5$.

Adding $[6,8]$, choosing $[4,6],[6,8]$ is optimal, answer is $8-4=4$.

Removing $[4,6]$, choosing $[1,5],[6,8]$ is optimal, answer is $8-1=7$.

### Subtasks

**This problem uses batched testing**

- Subtask 1 ($12$ points): $Q \le 500$.
- Subtask 2 ($32$ points): $Q \le 1.2 \times 10^4$.
- Subtask 3 ($28$ points): $Q \le 5 \times 10^4$.
- Subtask 4 ($16$ points): For any two intervals $(l_1, r_1)$ and $(l_2, r_2)$, it is guaranteed that $r_1 < l_2$ or $r_2 < l_1$.
- Subtask 5 ($12$ points): No additional constraints.

For $100\%$ of the data, it is guaranteed that $1 \le Q \le 5 \times 10^5$ and $1 \le l, r \le 10^6$.

### Notes

This problem is adapted from the [Canadian Computing Olympiad 2020](https://cemc.math.uwaterloo.ca/contests/computing/2020/) [Day 2](https://cemc.math.uwaterloo.ca/contests/computing/2020/cco/day2.pdf) T2 Interval Collection.

The data for this problem has been slightly modified.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
