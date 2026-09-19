Given a rooted tree with $n$ nodes, where the $i$-th node is numbered $i$.

There are $m$ queries, each query provides $l, r, x$, and you need to find out how many pairs of node numbers $(i, j)$ satisfy $l \le i < j \le r$ and the lowest common ancestor of $i$ and $j$ is node $x$.

## Input Format

The first line contains three numbers $n$, $m$, and $rt$, where $rt$ represents the root node's number.

The next $n-1$ lines, each containing two numbers $u$ and $v$, represent an edge.

The following $m$ lines, each containing three numbers $l$, $r$, and $x$, represent a query.

## Output Format

Output $m$ lines, each representing the answer to the corresponding query.

## Sample Input and Output

### Input Sample #1

```
10 10 7
4 2
10 4
3 2
6 10
9 2
7 3
1 4
8 2
5 3
8 10 10
2 6 2
3 6 2
4 6 4
3 10 2
8 8 10
3 10 4
2 3 2
2 6 4
1 7 10
```

### Output Sample #1

```
0
2
0
1
7
0
2
0
1
0
```

## Notes/Hints

Idea: Ynoi, Solution: nzhtl1477, Code: nzhtl1477, Data: nzhtl1477

For $100\%$ of the data, $1 \le n, m \le 2 \cdot 10^5$, $1 \le l, r, x \le n$.

#### Sample Explanation ####

`2 6 2`: The pairs that meet the criteria are $(2, 4)$ and $(2, 6)$.

`4 6 4`: The pair that meets the criteria is $(4, 6)$.

`3 10 2`: The pairs that meet the criteria are $(4, 8)$, $(4, 9)$, $(6, 8)$, $(6, 9)$, $(8, 9)$, $(8, 10)$, and $(9, 10)$.

`3 10 4`: The pairs that meet the criteria are $(4, 6)$ and $(4, 10)$.

`2 6 4`: The pair that meets the criteria is $(4, 6)$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
