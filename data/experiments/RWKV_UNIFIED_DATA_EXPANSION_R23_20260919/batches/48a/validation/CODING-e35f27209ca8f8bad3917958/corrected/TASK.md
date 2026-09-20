Windy has a rectangular land divided into $N \times M$ $1 \times 1$ small grids. Some of these grids contain obstacles. If it is possible to move from grid A to grid B, the distance between them is the Euclidean distance between the centers of the two grids. If it is not possible to move from grid A to grid B, there is no distance between them. A move from grid X to grid Y is possible if they share a common edge and neither X nor Y contains an obstacle. If Windy can remove $T$ obstacles, find the maximum distance between any two grids. It is guaranteed that after removing $T$ obstacles, at least one grid will not contain an obstacle.

## Input Format

The first line contains three integers, $N, M, T$. The next $N$ lines each contain a string of length $M, where `0` represents an empty grid and `1` represents a grid with an obstacle.

## Output Format

Output a floating-point number, rounded to 6 decimal places.

## Sample Input and Output

### Sample Input #1

```
3 3 0
001
001
110
```

### Sample Output #1

```
1.414214
```

### Sample Input #2

```
4 3 0
001
001
011
000
```

### Sample Output #2

```
3.605551
```

### Sample Input #3

```
3 3 1
001
001
001
```

### Sample Output #3

```
2.828427
```

## Notes

- $20\%$ of the data satisfies $1 \le N, M \le 30$ and $0 \le T \le 0$.
- $40\%$ of the data satisfies $1 \le N, M \le 30$ and $0 \le T \le 2$.
- $100\%$ of the data satisfies $1 \le N, M \le 30$ and $0 \le T \le 30$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
