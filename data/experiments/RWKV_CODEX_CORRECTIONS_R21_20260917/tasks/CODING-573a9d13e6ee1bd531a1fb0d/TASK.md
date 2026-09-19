To enhance her intelligence, ZJY starts learning linear algebra.

Her friend Boluo poses a problem for her: Given a $n \times n$ matrix $B$ and a $1 \times n$ matrix $C$, find a $1 \times n$ 01 matrix $A$ such that $D = (A \times B - C) \times A^{\sf T}$ is maximized, where $A^{\sf T}$ is the transpose of $A$. Output the value of $D$.

## Input Format

The first line contains an integer $n$. The next $n$ lines represent the matrix $B$, where the $i$-th row and $j$-th column element is denoted by $B_{ij}$. The following line contains $n$ integers representing the matrix $C$. Each number in matrices $B$ and $C$ is a non-negative integer not exceeding $1000$.

## Output Format

Output a single integer, which is the maximum value of $D$.

## Sample Input and Output

### Input Sample #1

```
3
1 2 1
3 1 0
1 2 3
2 3 7
```

### Output Sample #1

```
2
```

## Notes/Hints

- For $30\%$ of the data, $n \leq 15$;
- For $100\%$ of the data, $1 \leq n \leq 500$;
- There are also two ungraded hack data sets in subtask 2, with the same data range as above.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
