Your task is to simulate the process of the game Othello. The rules of Othello are as follows: Black and White alternate turns placing disks, and each move must "sandwich" at least one of the opponent's disks. All disks of the opponent that are "sandwiched" by the newly placed disk are then flipped to your color. A sequence of contiguous like-colored disks is considered "sandwiched" if it is flanked on both ends by the opponent's disks (spaces are not allowed). As illustrated, there are $8$ valid moves for White, at positions $(2,3)$, $(3,3)$, $(3,5)$, $(3,6)$, $(6,2)$, $(7,3)$, $(7,4)$, and $(7,5)$. Placing a White disk at $(7,3)$ results in the depicted board state (note that two Black disks, one vertically and one diagonally, are flipped to White). Note that although the Black disk at $(4,6)$ is flanked, it is not flanked by the newly placed disk and thus remains Black.

You are given an $8 \times 8$ board and the player who will make the next move. You must handle three types of instructions:

The `L` instruction outputs all legal moves, listed from left to right (output `No legal move` if there are no valid moves).

The `M r c` instruction places a disk at $(r,c)$. If the current player has no legal moves, the player changes first before proceeding. Input is guaranteed to be valid. The output should show the total number of Black and White disks after the move.

The `Q` instruction quits the game and prints the current board (in the same format as input).

Thanks to @BFD_qt for the translation

## Input/Output Sample

### Input Sample #1

```
2
--------
--------
--------
---WB---
---BW---
--------
--------
--------
W
L
M35
L
Q
WWWWB---
WWWB----
WWB-----
WB------
--------
--------
--------
--------
B
L
M25
L
Q
```

### Output Sample #1

```
(3,5) (4,6) (5,3) (6,4)
Black - 1 White - 4
(3,4) (3,6) (5,6)
--------
--------
----W---
---WW---
---BW---
--------
--------
--------
No legal move.
Black - 3 White - 12
(3,5)
WWWWB---
WWWWW---
WWB-----
WB------
--------
--------
--------
--------
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
