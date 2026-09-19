In a grid of size $n \times m$ (with the bottom-left corner at $(1,1)$ and the top-right corner at $(m,n)$), there is a small ball (which can be considered as a point). There are horizontal and vertical lasers in the grid. There are $q$ queries, each providing the initial position, direction, speed, and duration of movement of the ball (see Input Format for specifics). The task is to determine the number of times the ball touches the lasers, counting a touch at an intersection only once.

When the ball hits the boundary, it bounces. Specifically, if the ball's $x$ coordinate increases by $vx$ and $y$ by $vy$ each second, upon hitting the top or bottom boundary, $vy$ changes to $-vy$, and upon hitting the left or right boundary, $vx$ changes to $-vx$. For a clearer understanding, refer to the image in the Notes/Hints section.

## Input Format

The first line contains two integers $n$ and $m$, representing the number of rows and columns of the grid.

The next line is a string of length $n$ consisting of $0$s and $1$s. A $1$ at the $i$-th position indicates a laser in that row; otherwise, there is no laser.

The following line is a string of length $m$ consisting of $0$s and $1$s. A $1$ at the $i$-th position indicates a laser in that column; otherwise, there is no laser.

The next line contains an integer $q$, representing the number of queries.

The following $q$ lines each contain five integers $x, y, vx, vy, t$, indicating that the ball starts at position $(x, y)$, with $x$ increasing by $vx$ and $y$ by $vy$ each second, for a total of $t$ seconds. It is guaranteed that $vx$ and $vy$ are either $1$ or $-1$.

## Output Format

For each query, output a single line containing an integer, which is the number of times the ball touches the lasers.

## Sample Input and Output

### Input Sample #1

```
4 6
1010
010110
1
5 2 1 1 8
```

### Output Sample #1

```
6
```

## Notes/Hints

![Image](https://cdn.luogu.com.cn/upload/image_hosting/qclq5mux.png)

$1 \leq n, m \leq 10^5$, $1 \leq q \leq 10^4$, $1 \leq t \leq 10^9$, the initial position of the ball is within the grid and not on the boundary, and $vx, vy$ are either $1$ or $-1$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
