### Problem Description
There are $V$ nodes, and every pair of nodes is connected by an undirected edge with a weight of $T$. Your task is to find the shortest path that passes through $E$ specified edges.

### Input Format
**There are multiple test cases.** Each test case begins with a line containing three integers: $V(1 \le V \le 1000)$, $E(0 \le E \le V \times (V-1)/2)$, and $T(1 \le T \le 10)$. This is followed by $E$ lines, each containing two integers $a$ and $b$ $(1 \le a, b \le V, a \ne b)$, indicating a specified edge $<a, b>$. The input ends with a line containing three zeros.

### Output Format
For each test case, output the case number and the length of the shortest path.

## Sample Input

### Sample Input #1

```
5 3 1
1 2
1 3
4 5
4 4 1
1 2
1 4
2 3
3 4
0 0 0
```

### Sample Output #1

```
Case 1: 4
Case 2: 4
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
