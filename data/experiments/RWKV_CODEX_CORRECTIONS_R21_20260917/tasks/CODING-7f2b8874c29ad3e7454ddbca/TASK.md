## Problem Description

Given an undirected graph, find the smallest $k$ such that the nodes can be divided into $k$ sets, with no edges between nodes in the same set.

## Input and Output Format

### Input Format

The first line contains three integers: $n, m, k_0$, representing $n$ nodes, $m$ edges, and your $k$ needs to satisfy $k \le k_0$ to get full marks.

The next $m$ lines each contain two numbers $x, y$, describing an edge $(x, y)$. $(1 \le x, y \le n, x \ne y)$

### Output Format

Two lines. The first line contains an integer $k$, your answer. $(1 \le k \le n)$

The second line contains $n$ integers, the $i$-th integer represents the set number $a_i$ to which node $i$ is assigned. $(1 \le a_i \le k)$

## Sample Input and Output

### Sample Input #1

```
3 3 3
1 2
2 3
3 1
```

### Sample Output #1

```
3
1 2 3
```

## Notes

For each test case:

- If your output is invalid, you will receive 0 points.
- If $k \le k_0$, you will receive full marks.
- Otherwise, you will receive (let the full marks for this test case be $a$): $\lfloor a \times \dfrac{k_0}{k} \rfloor$ points.

There are 18 test cases in total, all of which satisfy $1 \le n \le 10^5$, $1 \le m \le 5 \times 10^5$, and guarantee the existence of a solution where $k \le k_0$. The following table shows the points for each test case:

| Test Case Number | Points |
| :--------------: | :----: |
| $1 \sim 4$       | $4$    |
| $5 \sim 6$       | $5$    |
| $7 \sim 17$      | $6$    |
| $18$             | $8$    |

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
