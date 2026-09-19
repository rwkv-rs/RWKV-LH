A knight on an $m \times n$ rectangular chessboard moves in an "L" shape (two squares in one direction and one square in an orthogonal direction). The task is to determine the maximum number of squares the knight can visit (including the starting point, excluding the endpoint) while ensuring that its path forms a simple polygon. This means that the line segments connecting the centers of the squares it jumps between must not intersect or touch, except at their common endpoints.

## Input Format

A single line containing two integers $m$ $(1 \le m \le 8)$ and $n$ $(1 \le n \le 10^{15})$, representing the dimensions of the chessboard.

## Output Format

Output a single integer, which is the maximum number of squares the knight can visit under the given constraints. If no such path exists, output $0$.

## Sample Input and Output

### Input Sample #1

```
6 6
```

### Output Sample #1

```
12
```

### Input Sample #2

```
8 3
```

### Output Sample #2

```
6
```

### Input Sample #3

```
7 20
```

### Output Sample #3

```
80
```

### Input Sample #4

```
2 6
```

### Output Sample #4

```
0
```

## Notes

Time limit: 2 seconds, Memory limit: 1024 MB.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
