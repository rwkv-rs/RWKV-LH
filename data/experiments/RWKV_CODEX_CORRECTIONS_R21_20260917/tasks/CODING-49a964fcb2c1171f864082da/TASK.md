Given an adjacency matrix of a directed graph with $n$ vertices, where self-loops are not included, find the transitive closure of the directed graph.

The adjacency matrix of a graph is defined as an $n \times n$ matrix $A = (a_{ij})_{n \times n}$, where

$$ a_{ij} = \left\{
\begin{aligned}
1, & \text{if there is a direct edge from } i \text{ to } j \\
0, & \text{if there is no direct edge from } i \text{ to } j \\
\end{aligned}
\right.
$$

The transitive closure of a graph is defined as an $n \times n$ matrix $B = (b_{ij})_{n \times n}$, where

$$ b_{ij} = \left\{
\begin{aligned}
1, & \text{if } i \text{ can reach } j \text{ directly or indirectly} \\
0, & \text{if } i \text{ cannot reach } j \text{ directly or indirectly} \\
\end{aligned}
\right.
$$

## Input Format

The input consists of $n+1$ lines.

The first line contains a positive integer $n$.

Lines $2$ to $n+1$ each contain $n$ integers, where the integer at the $j$-th column of the $(i+1)$-th line is $a_{ij}$.

## Output Format

The output consists of $n$ lines.

Lines $1$ to $n$ each contain $n$ integers, where the integer at the $j$-th column of the $i$-th line is $b_{ij}$.

## Sample Input and Output

### Input Sample #1

```
4
0 0 0 1
1 0 0 0
0 0 0 1
0 1 0 0
```

### Output Sample #1

```
1 1 0 1
1 1 0 1
1 1 0 1
1 1 0 1
```

## Notes/Hints

For $100\%$ of the data, $1 \le n \le 100$, and it is guaranteed that $a_{ij} \in \{0, 1\}$ and $a_{ii} = 0$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
