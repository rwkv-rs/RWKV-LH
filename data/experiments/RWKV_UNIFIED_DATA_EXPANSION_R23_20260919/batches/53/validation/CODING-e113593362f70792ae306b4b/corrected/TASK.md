If every edge of a complete undirected graph (where any two distinct vertices are connected by exactly one edge) is colored with a specific color, we call such a graph a colored graph. Two colored graphs are considered isomorphic if they have the same number of vertices and there exists a permutation of vertex numbering that makes the corresponding edges of the two graphs identical in color. The following two graphs are isomorphic because if you permute the vertices of the first graph $(1,2,3,4)$ to match the second graph $(4,3,2,1)$, they become identical.

![](https://cdn.luogu.com.cn/upload/pic/13240.png)

Your task is to calculate, for all graphs with $n$ vertices and no more than $m$ colors, how many pairwise non-isomorphic graphs there can be. Since the final answer can be very large, you only need to output the result modulo $p$ ($p$ is a prime number).

## Input Format

The input file consists of a single line containing three positive integers $n, m, p$.

## Output Format

Output the total number modulo $p$.

## Sample Input and Output

### Sample Input #1

```
1 1 2
```

### Sample Output #1

```
1
```

### Sample Input #2

```
3 2 97
```

### Sample Output #2

```
4
```

### Sample Input #3

```
3 4 97
```

### Sample Output #3

```
20
```

## Notes/Hints

For $100\%$ of the data, $1 \leq n \leq 53$, $1 \leq m \leq 1000$, and $n < p \leq 10^9$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
