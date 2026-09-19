JYY is recently obsessed with puzzle games. As a computer scientist, JYY has a set of black and white puzzles, and he wants to arrange them in a way that maximizes the area of the largest all-white sub-rectangle in the final pattern.

JYY has a total of $S$ puzzles, numbered from $1$ to $S$. Each puzzle numbered $i$ is a square grid of $N$ rows and $N$ columns, where each cell is either black or white. Initially, JYY places these $S$ puzzles in order from left to right on a table, forming a large rectangle of $N$ rows and $M$ columns (where $M = \sum_{i=1}^S W_i$).

JYY then realizes that by changing the order of these $S$ puzzles, he can increase the area of the largest all-white sub-rectangle in the $N$ by $M$ large rectangle.

Now, JYY wants to know the best way to arrange these puzzles to achieve the maximum area of the all-white sub-rectangle. Please help him calculate the optimal arrangement.

## Input Format

The first line contains an integer $T$, representing the number of test cases. The following lines describe each test case in order.

For each test case, the first line contains two integers $S$ and $N$.

The next $S$ sets of inputs correspond to the puzzles numbered $i$.

In the $i$-th set of inputs, the first line contains an integer $W_i$;

The next $N$ lines describe a $N$ by $W_i$ grid of $0/1$ values;

where a $0$ at position $(x, y)$ indicates the corresponding cell in the puzzle is white, and a $1$ indicates it is black.

## Output Format

For each test case, output a line containing an integer $ans$, which represents the maximum possible area of the all-white sub-rectangle.

## Sample Input and Output

### Input Sample #1

```
1
3 4
4
1001
0000
0010
1001
3
000
010
000
011
2
00
10
01
00
```

### Output Sample #1

```
6
```

## Notes/Hints

For $100\%$ of the data, it is guaranteed that $1 \le S, N, W \le 10^5$, $N \times \sum W_i \le 10^5$, and $1 \le T \le 3$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
