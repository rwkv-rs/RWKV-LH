As the winter solstice approaches, the days grow short and the nights long. The river is cold and pitch black, only the pink clouds in the east are visible. Outside the window, flocks of drowsy seagulls fly by, while inside, the aroma of morning cooking fills the air.

From morning to night, the hard work keeps one drowsy. Late at night, reading by the dim light, one finally retires to sleep. Please share the heavy responsibilities, and dance freely on the birthday in harmony.

## Problem Description

K's family has an unwritten rule. If there are only K and H at home, they decide who cooks by playing a game called "Three-Step Chess." This game is somewhat similar to Gomoku. As is well known, Gomoku is a game where the first player to connect five of their pieces wins. Like Gomoku, in Three-Step Chess, both players take turns placing pieces on a grid-shaped board and determine the winner based on whether a specified pattern is formed. However, there are differences:

1. Three-Step Chess does not distinguish between the players' pieces, meaning both players use the same color pieces;

2. The specified pattern cannot be rotated during judgment;

3. If the specified pattern is formed and the number of pieces on the board is exactly a multiple of 3, the player who forms the pattern wins; otherwise, that player loses (i.e., the other player wins).

For example, if the specified pattern is

```
.o
oo
```

and the current board state is

```
o..o.
o.o..
oo...
o.o..
o..o.
```

it is considered that the given pattern is not formed, where `o` represents a piece and `.` represents an empty space; but if a piece is placed at the second row and second column next, the specified pattern is formed, with the corresponding piece represented by `@`:

```
o..o.
o@o..
@@...
o.o..
o..o.
```

At this point, there are exactly 11 pieces on the board, and 11 is not a multiple of 3, so the player who placed the piece, i.e., the first player, loses the game.

At K's home, to save time, they usually play Three-Step Chess on a 5x5 initially empty board. Also, a randomly selected pattern consisting of no more than 4 pieces forming a connected block is used each time. Clearly, Three-Step Chess cannot end in a draw, so K and H agreed that the loser would be responsible for cooking. K wants to know if the game with the selected pattern is a **first-player win** if both she and H are smart enough; because if she has a better chance of winning, she would secretly let her younger sister win.

## Input Format

The input file contains multiple sets of data.

The first line of the input contains a positive integer $T$, indicating the number of data sets. It is guaranteed that $1 \le T \le 200$.

For each set of data, the input consists of 5 lines, each containing a string of length 5 consisting only of `.` and `o`, representing the specified pattern. It is guaranteed that each set of data contains at least one `o`, and all `o` form a connected block of size no more than 4.

## Output Format

For each set of data, output one line. If the input pattern is a **first-player win**, output `Far`; otherwise, output `Away`.

## Sample Input and Output

### Sample Input #1

```
3
.....
oo...
.....
.....
.....
.o...
.o...
.....
.....
.....
.....
.....
.....
.ooo.
.....
```

### Sample Output #1

```
Far
Far
Away
```

## Notes

### Sample #1 Explanation

This sample contains three sets of data.

The first set of data input pattern is a 1x2 `oo`. Clearly, no matter where the first player places their piece on the board, the second player has only two strategies:

- Connect with the first player's piece to form `oo`, in which case there are only 2 pieces on the board, so the second player immediately loses the game;

- Do not connect with the first player's piece to form `oo`, but when it's the first player's turn next, they can form `oo` anywhere, and there are exactly 3 pieces on the board, so the first player wins.

Either strategy results in the second player being unable to win, so for `oo`, the **first player always wins**.

The second set of data input pattern is a 2x1 pattern, similar to `oo`, it is known to be a **first player win**.

The third set of data input pattern is a 1x3 `ooo`, and it can be proven to be a first player loss.

### Subtasks

It is guaranteed that $1 \le T \le 200$. For each set of data, it is guaranteed that the 5x5 matrix of `.` and `o` contains at least one `o`, and all `o` form a connected block of size no more than 4.

### Problem Usage Agreement

From THUPC2024 (2024 Tsinghua University Student Programming Contest and University Invitational).

1. Any organization or individual may freely use or repost the problems from this repository;

2. Any organization or individual using the problems from this repository should do so without charge and openly, and must not use these problems for profit or add special privileges to these problems;

3. If possible, please provide access to data, standard programs, and problem solutions when using the problems from this repository; otherwise, please include the GitHub address of this repository.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
