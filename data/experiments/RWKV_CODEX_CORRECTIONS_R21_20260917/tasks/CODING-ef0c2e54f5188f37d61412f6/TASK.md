Little Dima gave his little brother Petya an interactive chess board of size \( n \times m \) as a present. There are many awesome features of this board, but one is Petya's favorite. He can choose any rectangle formed by board squares and perform an inversion. Every white cell in the inverted rectangle becomes black and every black one becomes white.

In the initial state, the board is colored in a chess style, meaning every cell is either black or white and every two cells that share a side have different colors. Little Petya wants to perform several inversions described above to turn all cells into the same color. He is impatient, so he asks you to provide him with instructions to do it with the minimal number of inversions.

## Input Format

Contains two integers \( n \) and \( m \) (\( 1 \le n, m \le 50 \)) - the number of rows and columns on the board, respectively.

## Output Format

The first line must contain the number of inversions \( k \) required to transform the board.

The following \( k \) lines must describe inversions, one per line. Each line must contain 4 integers - row and column of one of the corners of the corresponding rectangle and row and column of the opposite corner. Any two opposite corners can be used to specify a rectangle.

Rows of the board are numbered from 1 to \( n \). Columns of the board are numbered from 1 to \( m \).

## Sample Input and Output

### Input Sample #1

```
2 2
```

### Output Sample #1

```
2
1 1 1 1
2 2 2 2
```

## Notes

Time limit: 1 second, Memory limit: 256 MB.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
