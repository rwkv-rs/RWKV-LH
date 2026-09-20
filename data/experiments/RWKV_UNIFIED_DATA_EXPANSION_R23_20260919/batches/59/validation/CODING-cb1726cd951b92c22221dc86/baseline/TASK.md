Farmer John has a large field, which can be considered as an $N \times N$ square grid. The southwest corner is at coordinates $(0,0)$, and the northeast corner is at coordinates $(N-1, N-1)$.

In some grid cells, there are double-headed sprinklers, each capable of simultaneously spraying water and fertilizer. A double-headed sprinkler located at $(i,j)$ will:
- Sprinkles water on all grid cells $(x,y)$ where $N \geq x \geq i$ and $N \geq y \geq j$.
- Sprinkles fertilizer on all grid cells $(x,y)$ where $0 \leq x \leq i$ and $0 \leq y \leq j$.

Farmer John wants to cut out a rectangle in this field to plant sweet corn. The sides of the rectangle must not cut through any grid cells. All grid cells within the rectangle must be irrigated and fertilized by the double-headed sprinklers.

Determine the number of ways to cut such a rectangle. Since the number may be very large, output it modulo $10^9 + 7$.

## Input Format

The first line contains a single integer $N$, representing the size of the farm.

The next $N$ lines each contain two space-separated integers $i$ and $j$, indicating that there is a double-headed sprinkler at $(i, j)$.

It is guaranteed that there is exactly one sprinkler in each column and exactly one sprinkler in each row. In other words, no two sprinklers share the same x-coordinate or y-coordinate.

## Output Format

Output a single integer, which is the number of valid rectangle cutting schemes modulo $10^9 + 7$.

## Sample Input and Output

### Input Sample #1

```
5
0 4
1 1
2 2
3 0
4 3
```

### Output Sample #1

```
21
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
