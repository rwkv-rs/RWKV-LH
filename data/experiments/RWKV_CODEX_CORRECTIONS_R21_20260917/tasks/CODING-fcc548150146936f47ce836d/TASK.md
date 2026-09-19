You have $n$ vertices. You can connect undirected edges between these $n$ vertices. There can be at most one edge between any two vertices, and self-loops are not allowed. The maximum number of edges you can connect is obviously $\dfrac{n(n-1)}{2}$. However, there is an additional constraint: the graph must not have a non-trivial automorphism.

A graph $G$ has a non-trivial automorphism if there exists a permutation $p(1)$ to $p(n)$ of the numbers from $1$ to $n$ such that for all vertices $u, v$, there is an edge between $(u, v)$ if and only if there is an edge between $(p(u), p(v))$, and this permutation is non-trivial, meaning there exists a vertex $u$ such that $p(u) \ne u$.

For example, for a graph with 5 vertices $(1,2),(2,3),(3,4),(4,5),(5,1),(1,3)$, the permutation $p(1)=3$, $p(2)=2$, $p(3)=1$, $p(4)=5$, $p(5)=4$ is a non-trivial automorphism of this graph.

You need to answer the maximum number of edges in an undirected simple graph with $n$ vertices that does not have a non-trivial automorphism. If no such graph exists for $n$ vertices, output `-1`. Otherwise, output the answer modulo $10^9+7$.

## Input Format

**This problem contains multiple test cases.**  
A line with a positive integer $T$ indicates the number of test cases.  
For each test case:  
A positive integer $n$ represents the number of vertices in the graph you need to answer.

## Output Format

For each test case:  
A line with an integer representing the answer modulo $10^9+7$. If no graph with $n$ vertices satisfies the condition, output `-1`.

## Sample Input and Output

### Input Sample #1

```
6
1
2
3
4
5
6
```

### Output Sample #1

```
0
-1
-1
-1
-1
9
```

## Notes/Hints

| Test Point | Data Range |
|:-:|:-:|
| $1$ | $n, T \le 6$ |
| $2$ | $n, T \le 10$ |
| $3, 4$ | $n, T \le 100$ |
| $5, 6$ | $n \le 10^5$ |
| $7, 8$ | $n \le 10^9$ |
| $9$ | $n \le 10^{18}$ |
| $10$ | $n = 10^{100}$ |

For $100\%$ of the data, $1 \le n \le 10^{100}$, $1 \le T \le 10^4$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
