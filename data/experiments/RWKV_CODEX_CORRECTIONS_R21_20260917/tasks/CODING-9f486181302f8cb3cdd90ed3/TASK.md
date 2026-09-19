Define a black-and-white replication process where each cell updates its state by examining its own state and those of its eight surrounding neighbors. If an odd number of these nine cells are black, the cell becomes black; otherwise, it becomes white. Unfortunately, there is a bug in the replication process: after each update, one arbitrary cell may spontaneously flip its state (from black to white or vice versa, or remain unchanged). Given the final result of this flawed replication process, which consists of \( w \) rows and \( h \) columns, find the smallest initial pattern of black and white cells that could have led to this final result through the replication process and the bug.

`#` represents a black cell, and `.` represents a white cell.

Note that if there are extra white cells, they should be omitted. For example, the left pattern can be reduced to the right pattern:

```
...........   .....##..#
......##..#   #........#
.#........#   #..#...#..
.#..#...#..   .#.......#
..#.......#
...........
...........
```

Constraints: \( 1 \le w, h \le 300 \).

## Input Format

The first line of input contains two integers \( w \) and \( h \) (\( 1 \le w, h \le 300 \)), representing the width and height of the final pattern's bounding box. Following this are \( h \) lines, each containing \( w \) characters, describing the final pattern. Each character is either `.` (empty cell) or `#` (filled cell). There is at least one filled cell in the first row, the last row, the first column, and the last column.

## Output Format

Display a minimum-size, non-empty pattern that could have resulted in the given pattern, assuming that at each stage of the replication process, at most one cell spontaneously changed state. The size of a pattern is the area of its bounding box. Use `.` for empty cells and `#` for filled cells. Use the minimum number of rows and columns needed to display the pattern.

## Sample Input and Output

### Sample Input #1

```
10 10
.#...#...#
##..##..##
##.#.##...
##.#.##...
.#...#####
...##..#.#
......###.
##.#.##...
#..#..#..#
##..##..##
```

### Sample Output #1

```
.#
##
```

### Sample Input #2

```
8 8
##..#.##
#.####.#
.#.#.#..
.##.#.##
.#.#.#..
.##.#.##
#..#.###
##.#.##.
```

### Sample Output #2

```
####
#..#
#.##
###.
```

### Sample Input #3

```
5 4
#....
..###
..###
..###
```

### Sample Output #3

```
#
```

## Notes/Hints

Time limit: 3 seconds, Memory limit: 512 MB.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
