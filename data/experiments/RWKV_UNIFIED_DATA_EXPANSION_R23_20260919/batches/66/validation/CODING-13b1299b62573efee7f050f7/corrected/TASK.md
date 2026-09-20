Little AA and Little YY have obtained movie tickets for "Pleasant Goat and Big Big Wolf" and both are eager to watch it. However, there is only one ticket, so they decide to settle the matter through a game of wits, with the winner getting the ticket.

In a maze of size $N \times M$, a piece is placed, and Little AA chooses the initial position of the piece arbitrarily. Then, Little YY and Little AA take turns moving the piece to an adjacent cell. The rules of the game stipulate that a cell cannot be entered twice in one game, and the piece cannot be moved into certain cells. When a player can no longer move the piece, the game ends, and the last player to move the piece wins the game.

For example, in the maze shown below, `.` represents a cell the piece can pass through, and `#` represents a cell the piece cannot pass through:

```cpp
                                 .##
                                 ...
                                 #.# 
```
If Little AA places the piece at $(1,1)$, Little AA cannot win the game no matter what.

However, if Little AA places the piece at $(3,2)$ or $(2,3)$, Little AA can win the game. For instance, if Little AA places the piece at $(3,2)$, Little YY can only move it to $(2,2)$, at which point Little AA moves the piece to $(2,3)$ and wins the game.

Both Little AA and Little YY are extremely intelligent and never make mistakes. Can Little AA win this game and thus obtain the precious movie ticket?

## Input Format

The input data starts with two integers $N, M$, indicating the dimensions of the maze.

Next, $N$ lines follow, each containing $M$ characters, describing the maze.

## Output Format

If Little AA can win the game, output one line `WIN`, followed by all starting positions from which Little AA can win, listed in row-major order, each on a new line.

Otherwise, output one line `LOSE`.

## Sample Input and Output

### Sample Input #1

```
3 3
.##
...
#.#
```

### Sample Output #1

```
WIN
2 3
3 2
```

## Notes

- For $30\%$ of the data, $n, m \leq 5$;
- For $100\%$ of the data, $1 \leq n, m \leq 100$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
