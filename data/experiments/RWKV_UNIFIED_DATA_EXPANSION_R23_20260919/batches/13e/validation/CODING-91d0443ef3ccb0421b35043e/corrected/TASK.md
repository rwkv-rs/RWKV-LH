Given a directed graph with $N$ vertices and $M$ edges, for each vertex $v$, determine $A(v)$, which represents the largest vertex number that can be reached starting from vertex $v$.

## Input Format

The first line contains two integers $N$ and $M$, representing the number of vertices and edges, respectively.

The following $M$ lines each contain two integers $U_i$ and $V_i$, representing the edge $(U_i, V_i)$. Vertices are numbered from $1$ to $N$.

## Output Format

A single line containing $N$ integers $A(1), A(2), \dots, A(N)$.

## Sample Input and Output

### Input Sample #1

```
4 3
1 2
2 4
4 3
```

### Output Sample #1

```
4 4 3 4
```

## Notes

- For $60\%$ of the test cases, $1 \leq N, M \leq 10^3$.
- For $100\%$ of the test cases, $1 \leq N, M \leq 10^5$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
