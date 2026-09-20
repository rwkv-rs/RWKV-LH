## Problem Description

The cave is represented as an $N*N$ grid, where each cell is denoted by $(X,Y)$, with $1 \le X,Y \le N$. Here, $X$ represents the row number from top to bottom, and $Y$ represents the column number from left to right. The cell $(1,1)$ is at the top-left corner, $(1,N)$ at the top-right corner, $(N,1)$ at the bottom-left corner, and $(N,N)$ at the bottom-right corner.

Cells where $X+Y$ is odd have an instability value $V_{X,Y}$, while cells where $X+Y$ is even have an instability value of $0$.

**ZRQ** has exactly $M$ pillars that can support the cave, and the strength of each pillar is considered infinite.

Placing a pillar on a cell reduces its instability to $0$.

Each pillar is L-shaped and occupies the current cell plus two adjacent cells (forming an L-shape, with four possible orientations).

![L-shaped pillar](https://cdn.luogu.com.cn/upload/pic/13049.png)

The adjacent cells occupied by the pillar do not reduce their instability (i.e., the pillar's strength is only at the corner).

Some cells have already collapsed and cannot have pillars placed on them, nor can they be occupied. There are $K$ such collapsed cells (their instability is $0$, even if $X+Y$ is odd).

**ZRQ** wants to know the minimum sum of instability values after placing some pillars (not necessarily all $M$ pillars).

## Input Format

The first line contains three integers $N, M, K$.

The next $N$ lines contain $N$ integers each, representing the instability values of the cells, ensuring that cells where $X+Y$ is even and already collapsed cells have an instability value of $0$.

The next $K$ lines contain two integers $X, Y$ each, representing the coordinates of the collapsed cells.

## Output Format

A single integer representing the minimum sum of instability values.

## Sample Input and Output

### Input Sample #1

```
3 3 1
0 1 0
2 0 1
0 1 0
1 3
```

### Output Sample #1

```
3
```

### Input Sample #2

```
3 3 4
0 2 0
0 0 4
0 3 0
1 3
2 1
2 2
3 1
```

### Output Sample #2

```
9
```

## Notes/Hints

There are 10 test cases, each worth 10 points, totaling 100 points.

For test cases 1 to 3, $1 \le N \le 6$.

For test cases 4 to 7, $1 \le N \le 11$.

For test cases 8 to 10, $1 \le N \le 50$.

For all test cases, $0 \le M \le \frac{N^2}{3}, 0 \le K \le N^2, 0 \le V_{X,Y} \le 10^6$.

**Explanation for Sample #1:**

It is clear that no two unstable cells can be covered by a corner, so placing a pillar at $(2,1)$ is sufficient. The remaining instability is $V_{1,2} + V_{2,3} + V_{3,2} = 1 + 1 + 1 = 3$.

**Explanation for Sample #2:**

No pillars can be placed, so the remaining instability is $V_{1,2} + V_{2,3} + V_{3,2} = 2 + 4 + 3 = 9$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
