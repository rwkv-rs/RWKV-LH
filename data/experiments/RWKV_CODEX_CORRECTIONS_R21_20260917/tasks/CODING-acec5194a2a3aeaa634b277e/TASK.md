Little L has many favorite game characters, and he connects these characters based on certain relationships. These game characters and their relationships form a tree, which Little L calls the "Relationship Tree."

## Problem Description

The Relationship Tree consists of $n$ nodes and $n-1$ undirected edges.

For a given graph $G$, the **vertex-induced subgraph** of graph $G$ with respect to the set of vertices $E$ is the graph consisting of the set $E$ and all edges in the original graph $G$ whose both endpoints are in $E$.

A graph is defined as **neat** if and only if for any two vertices $u, v$ in the graph, $u$ and $v$ are either **not connected** or **have a distance of no more than** $k$.

Little L wants to know, for a given pair of integers $l, r$ (where $l \leq r$), how many pairs $(a, b)$ satisfy $l \leq a \leq b \leq r$ such that the vertex-induced subgraph consisting of all nodes with indices between $a$ and $b$ (inclusive) is **neat**. Additionally, he wants to know the sum of all interval lengths (i.e., $b-a+1$).

Since Little L likes to ask questions, you need to answer $q$ such queries.

## Input Format

The first line contains three integers $n$, $q$, and $k$, as described above.

The next $n-1$ lines each contain two integers $u$ and $v$, describing an edge.

The next $q$ lines each contain two integers $l$ and $r$, representing a query.

## Output Format

Output $q$ lines, each containing two integers, representing the number of pairs $(a, b)$ that satisfy the condition and the sum of all interval lengths, respectively.

## Sample Input and Output

### Input Sample #1

```
5 3 2
1 2
1 5
4 5
3 5
1 3
2 5
1 5
```

### Output Sample #1

```
6 10
10 20
14 30
```

## Notes

### Sample 1 Explanation

The formed Relationship Tree is shown in the image.

The pairs $(a, b)$ that satisfy the condition are $(1,1),(1,2),(1,3),(1,4),(2,2),(2,3),(2,4),(2,5),(3,3),(3,4),(3,5),(4,4),(4,5),(5,5)$.

The answers for the three queries are $6,10$, $10,20$, and $14,30$, respectively.

--------------------------------

### Data Size and Constraints

**This problem uses batched testing.**

+ Subtask 1 ( $10\%$ ): $n \leq 2000$.
+ Subtask 2 ( $30\%$ ): $n \leq 2 \times 10^4$, and the formed Relationship Tree is a chain.
+ Subtask 3 ( $60\%$ ): $n \leq 2 \times 10^4$.
+ Subtask 4 (Enhanced data, time limit $4.5s$): No special restrictions.

For $100\%$ of the test cases, it is guaranteed that $1 \leq n \leq 8 \times 10^4$, $1 \leq q \leq 10^5$, $0 \leq k < n$, and $1 \leq u, v, l, r \leq n$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
