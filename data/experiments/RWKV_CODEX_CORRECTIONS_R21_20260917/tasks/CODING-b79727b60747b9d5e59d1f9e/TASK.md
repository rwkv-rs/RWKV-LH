**[Problem Description]**

The first line contains an integer $T$, indicating the number of data sets.

For each data set, the first line contains two integers $V$, $E$, representing the highest numbered vertex and the number of edges, respectively.

The next $m$ lines each contain two integers $u$, $v$ and a string $c$, indicating there is an edge from vertex $u$ to vertex $v$. If $c = \texttt{D}$, it is a directed edge; if $c = \texttt{U}$, it is an undirected edge.

For each data set, output its Euler circuit. If no Euler circuit exists, output `No euler circuit exist`.

Tips: Each output should be followed by two new lines.

**[Data Constraints]**

For $100\%$ of the data, $1 \leq V \leq 100$, $1 \leq E \leq 500$.

## Sample Input

### Input Sample #1

```
2
6 8
1 3 U
1 4 U
2 4 U
2 5 D
3 4 D
4 5 U
5 6 D
5 6 U
4 4
1 2 D
1 4 D
2 3 U
3 4 U
```

## Output Sample

### Output Sample #1

```
1 3 4 2 5 6 5 4 1
No euler circuit exist
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
