Thanks to hzwer for the point divide and conquer mutual evaluation.

## Problem Description

Given a tree with $n$ nodes, query whether there exists a pair of nodes with a distance of $k$ on the tree.

## Input Format

The first line contains two numbers $n$ and $m$.

From the second to the $n$-th line, each line contains three integers $u$, $v$, and $w$, representing that there is a path with weight $w$ connecting nodes $u$ and $v$ on the tree.

The next $m$ lines, each containing a single integer $k$, represent the queries.

## Output Format

For each query, output a line with a string representing the answer. If the pair exists, output `AYE`; otherwise, output `NAY`.

## Sample Input and Output

### Input Sample #1

```
2 1
1 2 2
2
```

### Output Sample #1

```
AYE
```

## Notes

### Data Size and Constraints

- For $30\%$ of the data, it is guaranteed that $n \leq 100$.
- For $60\%$ of the data, it is guaranteed that $n \leq 1000$, $m \leq 50$.
- For $100\%$ of the data, it is guaranteed that $1 \leq n \leq 10^4$, $1 \leq m \leq 100$, $1 \leq k \leq 10^7$, $1 \leq u, v \leq n$, $1 \leq w \leq 10^4$.

### Hints

- **This problem does not require optimization for speed**.
- If you are consistently getting RE/TLE on test case #7, you might want to check out [this post](https://www.luogu.com.cn/discuss/show/188596). Note that the first solution mentioned in the post also has the issues described, but since these issues are not related to the point divide and conquer algorithm itself, and the solution quality is very high, it is not being removed and is provided for reference only.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
