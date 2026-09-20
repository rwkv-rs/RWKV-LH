In search of the legendary treasure, Xiao Ming enters a maze, which we describe using a matrix of $r$ rows and $c$ columns. Each position in the matrix represents a square area:

- The character `.` indicates a passable square.
- The character `#` indicates an impassable square.
- There are $k$ mechanisms in the maze, with the $i$-th mechanism operating as follows:
  - Whenever Xiao Ming steps onto the square at row $r_i$, column $c_i$, the square at row $R_i$, column $C_i$ changes its state (if it is currently passable, it becomes impassable; if it is currently impassable, it becomes passable. The top-left square is at row 1, column 1).

Given the current position of Xiao Ming, the position of the treasure, the state of each square in the maze, and the descriptions of all mechanisms, determine the minimum number of steps Xiao Ming needs to take to reach the treasure (Xiao Ming cannot step outside the boundaries of the maze, and at the start, both the starting and treasure positions are passable. Mechanisms do not appear at the start or end points and do not affect these squares).

## Input Format

The first line of input contains two integers: $r$ and $c$.

The second line to the $(r+1)$-th line of input contains strings of length $c$, describing the current state of the maze: `.` indicates a passable square, `#` indicates an impassable square, `S` indicates the starting point, and `T` indicates the treasure's location.

The $(r+2)$-th line contains an integer $k$, the number of mechanisms. The next $k$ lines each contain four integers $r_i, c_i, R_i, C_i$, describing a mechanism.

## Output Format

Output a single integer: the minimum number of steps Xiao Ming needs to take to reach the treasure. The test data guarantees that the treasure can be found.

## Sample Input and Output

### Input Sample #1

```
5 5
S.#..
#####
..#..
##.#.
...#T
6
1 5 4 2
1 4 3 3
5 1 3 3
1 4 4 5
1 2 1 3
1 5 2 1
```

### Output Sample #1

```
22
```

## Notes

### Data Range and Constraints

For all data, $5 \le r, c \le 30$, $0 \le k \le 10$, $1 \le r_i, R_i \le r$, $1 \le c_i, C_i \le c$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
