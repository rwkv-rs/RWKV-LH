Given an $N \times N$ square grid, with its top-left corner designated as the starting point ◎, located at coordinates $(1,1)$. The $X$-axis extends to the right, and the $Y$-axis extends downward, with each grid cell having a side length of $1$, as illustrated below.

![Grid Illustration](https://cdn.luogu.com.cn/upload/pic/12156.png)

A car starts from the starting point ◎ and aims to reach the bottom-right corner, marked as the endpoint ▲, at coordinates $(N,N)$.

At several grid intersections, fuel depots are available to refuel the car during its journey. The car must adhere to the following rules while traveling:

1. The car can only travel along the grid edges. It can travel $K$ grid edges on a full tank of fuel. The car starts with a full tank and there are no fuel depots at the starting or ending points.

2. When the car traverses a grid edge, if either its $X$ or $Y$ coordinate decreases, it incurs a fee of $B$; otherwise, no fee is charged.

3. Upon encountering a fuel depot during travel, the car must refuel to full capacity and pay a refueling fee of $A$.

4. If necessary, a fuel depot can be added at any grid point, incurring an additional depot setup fee of $C$ (excluding the refueling fee $A$).

5. $N, K, A, B, C$ are all positive integers, subject to the constraints: $2 \leq N \leq 100, 2 \leq K \leq 10$.

Design an algorithm to determine the minimum cost for the car to travel from the starting point to the endpoint.

## Input Format

The first line of the input file contains the values of $N, K, A, B, C$.

The second line onwards, an $N \times N$ matrix of $0-1$ values is provided, with each line containing $N$ values, ending at line $N+1$.

A value of $1$ in the matrix at position $(i, j)$ indicates the presence of a fuel depot at the grid intersection $(i, j)$, while a value of $0$ indicates no depot. Adjacent numbers on each line are separated by spaces.

## Output Format

Upon completion of the program, output the minimum cost.

## Sample Input and Output

### Input Sample #1

```
9 3 2 3 6
0 0 0 0 1 0 0 0 0
0 0 0 1 0 1 1 0 0
1 0 1 0 0 0 0 1 0
0 0 0 0 0 1 0 0 1
1 0 0 1 0 0 1 0 0
0 1 0 0 0 0 0 1 0
0 0 0 0 1 0 0 0 1
1 0 0 1 0 0 0 1 0
0 1 0 0 0 0 0 0 0
```

### Output Sample #1

```
12
```

## Notes

$2 \leq N \leq 100, 2 \leq K \leq 10$

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
