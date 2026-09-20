There are $n$ boxes, each initially containing one chess piece.

Two players take turns to make moves. In each turn, a player can choose a chess piece from box $i$ and a positive integer $p$, moving the chess piece to the box numbered $2^p \times i$. If the box numbered $2^p \times i$ already contains a chess piece, both chess pieces are removed from the box. The player who cannot make a move loses.

Determine the $k$-th smallest $n$ such that the second player (the one who moves after the first player) can win the game.

## Input Format

A single line containing a positive integer $k$.

## Output Format

A single line containing a positive integer $n$.

## Sample Input and Output

### Sample Input #1

```
2
```

### Sample Output #1

```
10
```

## Notes/Hints

For $100\%$ of the data, $1 \le k < 10^9$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
