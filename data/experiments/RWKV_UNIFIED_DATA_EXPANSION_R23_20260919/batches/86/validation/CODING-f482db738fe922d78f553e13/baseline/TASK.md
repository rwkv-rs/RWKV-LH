Mr. Liu has recently been learning chess, using a game software called jloi-08. In this game, not only can you play against the computer normally, but you can also study famous chess games and receive rules guidance for beginners, among other rich features. However... it takes up 1.4G T\_T.

To get back on track, in this software, there are many interesting games designed to help players better understand and utilize various chess pieces. One such game is as follows:

Given a chessboard and some chess pieces, you are asked to place these pieces on the board such that they do not attack each other. Your score is determined by the number and types of pieces you place.

This game is quite complex, and Mr. Liu always fails to achieve a high score. Therefore, the computer has reduced the difficulty by placing some pieces for Mr. Liu, leaving only an arbitrary number of bishops for you to place.

Now, Mr. Liu wants to test you: on the chessboard provided by the computer, what is the maximum number of bishops you can place?

There are a total of 6 types of chess pieces in chess:

- king;
- queen;
- bishop;
- knight;
- rook;
- pawn.

The attack ranges of each piece are as follows:

- The queen can attack pieces in the same row, column, or diagonal;
- The knight's attack range is shown in the following image:

![](https://cdn.luogu.com.cn/upload/pic/2669.png)

- The rook attacks all squares in horizontal and vertical lines;
- The pawn attacks one square forward in both diagonal directions (forward means in the direction of increasing $x$, where $x$ is the row and $y$ is the column);
- The king attacks one square in all 8 surrounding directions;
- The bishop attacks all squares in both diagonals.

Except for the knight, all pieces' attack ranges are blocked by other pieces.

Unfortunately, the software is not perfect, and the pieces on the provided chessboard may attack each other, but you do not need to consider this. You only need to ensure that the bishops you place do not attack each other or the pre-placed pieces.

## Input Format

The first line contains two integers $x, y$ ($1 \leq x, y \leq 1024$).

The following $x$ lines, each containing $y$ characters, represent the chessboard.

Where: `K` - king, `Q` - queen, `B` - bishop, `N` - knight, `R` - rook, `P` - pawn, `.` - blank.

## Output Format

A single line containing a number, representing the maximum number of bishops that can be placed.

## Sample Input and Output

### Input Sample #1

```
3 3
..N
...
...
```

### Output Sample #1

```
2
```

## Notes

```plain
BBN
...
...
```

```plain
BBN
...
B..
```

Although the second method seems better, the knight is attacked by the bishop in the third row. This means you need to avoid two situations: bishops attacking each other and bishops attacking the pre-placed pieces; but you do not need to consider attacks between the pre-placed pieces.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
