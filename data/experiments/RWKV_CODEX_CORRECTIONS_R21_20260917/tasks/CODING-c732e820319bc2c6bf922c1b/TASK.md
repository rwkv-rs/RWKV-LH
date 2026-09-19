Given an undirected, weighted tree with $n$ nodes, each node has a unique identifier which is a permutation of numbers from $1$ to $n$.

There are $m$ queries, each query specifies a range $l, r$. The task is to find the sum of distances between all pairs of nodes $(i, j)$ such that $l \le i < j \le r$. The distance between two nodes is defined as the sum of the weights of the edges on the simple path connecting them.

## Input Format

The first line contains two space-separated integers $n$ and $m$.

The next $n-1$ lines each contain three space-separated integers $u$, $v$, and $d$, representing an edge between nodes $u$ and $v$ with weight $d$.

The following $m$ lines each contain two space-separated integers $l$ and $r$, representing a query.

## Output Format

Output $m$ lines, each containing the answer to the corresponding query, modulo $2^{32}$.

## Sample Input and Output

### Input Sample #1

```
6 6
2 1 1
5 1 1
3 1 3
4 5 1
6 3 3
2 5
1 5
1 4
3 6
2 6
1 1
```

### Output Sample #1

```
19
26
18
28
44
0
```

## Notes/Hints

For $100\%$ of the data, $1 \le n, m, d \le 2 \cdot 10^5$, and all values are integers.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
