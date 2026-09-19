Given a graph with $n$ vertices and $m$ edges, which **may contain multiple edges and self-loops**, please provide all algebraic representations of this graph.

## Input Format

The first line contains four positive integers $n$, $m$, $type1$, and $type2$. Here, $n$ and $m$ represent the number of vertices and edges in the graph, respectively. $type1 = 0$ indicates that the graph is undirected, and $type1 = 1$ indicates that the graph is directed. $type2 = 0$ indicates that the graph is not weighted, and $type2 = 1$ indicates that the graph is weighted.

If $type2 = 0$, the following $m$ lines each contain two positive integers $u$ and $v$ representing an edge.

If $type2 = 1$, the following $m$ lines each contain three positive integers $u$, $v$, and $d$ representing an edge, where $d$ is the weight of the edge.

## Output Format

Output the following algebraic representations in order:

1. Adjacency matrix or weight matrix. Output $n$ lines, each with $n$ numbers representing the matrix. Do not output if the graph has multiple edges. If $type2 = 0$, output the adjacency matrix; if $type2 = 1$, output the weight matrix.

2. Incidence matrix. Output $n$ lines, each with $m$ numbers representing the matrix. Do not output if $type2 = 1$ or if there are self-loops.

3. Adjacency list. Output $n$ lines. If $type2 = 0$, each line outputs $d_i$ numbers, where $d_i$ is the degree of node $i$ (undirected graph) or positive degree (directed graph), each number representing an edge connected to $i$. If $type2 = 1$, each line outputs $2d_i$ numbers, each pair representing an edge.

4. Forward list. If $type2 = 0$, output two lines representing vectors $A$ and $B$. If $type2 = 1$, output three lines representing vectors $A$, $B$, and $Z$.

5. Reverse list. Do not output if $type1 = 0$ (as the reverse list is the same as the forward list in this case). If $type2 = 0$, output two lines representing vectors $A$ and $B$. If $type2 = 1$, output three lines representing vectors $A$, $B$, and $Z$.

For adjacency list, forward list, and reverse list, all edges corresponding to each node should be output in the order of input.

**Note: The $A$ vector in the forward and reverse lists is an $n + 1$ dimensional vector. In directed graphs, $A(n + 1) = m + 1$, and in undirected graphs, $A(n + 1) = 2m + 1$.**

## Sample Input and Output

### Sample Input #1

```
3 3 0 0
2 3
1 3
1 2
```

### Sample Output #1

```
0 1 1
1 0 1
1 1 0
0 1 1
1 0 1
1 1 0
3 2
3 1
2 1
1 3 5 7
3 2 3 1 2 1
```

### Sample Input #2

```
3 3 1 1
3 1 5
2 2 4
3 1 3
```

### Sample Output #2

```
2 4
1 5 1 3
1 1 2 4
2 1 1
4 5 3
1 3 4 4
3 3 2
5 3 4
```

### Sample Input #3

```
3 3 0 1
1 3 5
2 2 3
2 3 1
```

### Sample Output #3

```
0 0 5
0 3 1
5 1 0
3 5
2 3 2 3 3 1
1 5 2 1
1 2 5 7
3 2 2 3 1 2
5 3 3 1 5 1
```

### Sample Input #4

```
4 3 0 1
3 3 5
2 4 6
2 4 7
```

### Sample Output #4

```
4 6 4 7
3 5 3 5
2 6 2 7
1 1 3 5 7
4 4 3 3 2 2
6 7 5 5 6 7
```

## Notes

For all data, it is guaranteed that $1 \le n \le 300$, $1 \le m \le 300$, and $1 \le edge weight \le 32768$.

**Detailed Hints:**

1. In undirected graphs, some arrays may require a length of $2m$, so be careful to avoid array overflow.

2. In undirected graphs, if there are self-loops, they need to be output twice in the adjacency list and forward list, but they do not affect the output of the adjacency matrix or weight matrix.

3. In the reverse list, edges leading to a node should also be output in the order of input, not in the order of edge weights.

4. In undirected weighted graphs, each non-self-loop edge modifies two positions in the weight matrix.

5. If you are unable to pass the test, you can check your code by constructing small datasets with directed/undirected, weighted/unweighted, with/without self-loops, and with/without multiple edges.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
