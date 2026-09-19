The Intelligent Beads Game board consists of a triangular piece and 12 unique parts. The board piece is shown in Figure 1.
![](https://cdn.luogu.com.cn/upload/pic/13767.png)
![](https://cdn.luogu.com.cn/upload/pic/13768.png)
![](https://cdn.luogu.com.cn/upload/pic/13769.png)
Each part made of beads can be placed at any position on the board, provided there is space and the size fits. All parts are allowed to be rotated (0º, 90º, 180º, 270º) and flipped (horizontally, vertically).

Given an initial layout of the board, find a feasible arrangement to place all 12 parts onto the board.

## Input Format

The file contains the initial description of the board, with 10 lines in total. The i-th line contains i characters. If the j-th character of the i-th line is a letter from 'A' to 'L', it indicates that the grid at the i-th row and j-th column already contains a part, with the part number corresponding to the letter. If the j-th character of the i-th line is '.', it indicates that the grid at the i-th row and j-th column is empty.
The input guarantees that the pre-placed parts are already on the board.

## Output Format

If a solution is found, print 10 lines to the output file, representing the layout after placing all 12 parts. The i-th line should contain i characters, where the j-th character of the i-th line indicates which part is placed at the i-th row and j-th column.
If no solution exists, output the string 'No solution' (without quotes, please note the capitalization).
All data guarantees that there is at most one solution.

## Sample Input and Output

### Input Sample #1

```
.
..
...
....
.....
.....C
...CCC.
EEEHH...
E.HHH....
E.........
```

### Output Sample #1

```
B
BK
BKK
BJKK
JJJDD
GJGDDC
GGGCCCI
EEEHHIIA
ELHHHIAAF
ELLLLIFFFF
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
