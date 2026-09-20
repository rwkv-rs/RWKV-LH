There is an $n \times n$ chessboard with the bottom-left corner at $(1,1)$ and the top-right corner at $(n,n)$. A piece at point $(x,y)$ can move one step to either $(x+1,y)$ or $(x,y+1)$.

There are $m$ pieces, with the $i$-th piece starting at $(a_i,1)$ and ending at $(b_i,n)$. Determine the number of ways for each piece to travel from its start to its end point such that the paths of all pieces do not intersect at any point. Output the number of such arrangements modulo $998244353$.

Two arrangements are considered different if and only if there is at least one point that is traversed by different pieces.

## Input Format

**This problem contains multiple test cases.**

The first line contains an integer $T$, indicating the number of test cases.

For each test case:

The first line contains two integers $n$ and $m$, representing the size of the chessboard and the number of start-end points, respectively.

The next $m$ lines each contain two integers $a_i$ and $b_i$, as described in the problem statement.

## Output Format

For each test case, output one line containing an integer representing the number of arrangements modulo $998244353$.

## Sample Input and Output

### Input Sample #1

```
3
3 2
1 2
2 3
5 2
1 3
3 5
10 5
3 5
4 7
5 8
7 9
9 10
```

### Output Sample #1

```
3
155
2047320
```

## Notes

- For $30\%$ of the data, $n \leq 100$ and $m \leq 8$.
- For $100\%$ of the data, $T \leq 5$, $2 \leq n \leq 10^6$, $1 \leq m \leq 100$, $1 \leq a_1 \leq a_2 \leq \dots \leq a_m \leq n$, $1 \leq b_1 \leq b_2 \leq \dots \leq b_m \leq n$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
