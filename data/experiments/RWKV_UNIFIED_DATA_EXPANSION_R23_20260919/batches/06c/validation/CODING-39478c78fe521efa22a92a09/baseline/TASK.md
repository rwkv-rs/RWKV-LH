NOIP2017 Junior Group T3

## Problem Description

There is a $m \times m$ chessboard where each square can be red, yellow, or colorless. You need to travel from the top-left corner to the bottom-right corner of the board.

At any moment, the square you are standing on must be colored (not colorless), and you can only move up, down, left, or right. When moving from one square to another, if the colors of the two squares are the same, you do not need to spend any gold coins; if they are different, you need to spend 1 gold coin.

Additionally, you can spend 2 gold coins to cast a spell that temporarily changes the next colorless square to a color of your choice. However, this spell cannot be used consecutively, and its effect is short-lived. That is, if you use this spell and step onto the temporarily colored square, you cannot use the spell again immediately; you can only use it again when you move off that square to another square that already has a color. When you leave that square (the one made colored by the spell), it reverts to being colorless.

You need to travel from the top-left corner to the bottom-right corner of the chessboard, and you are to find the minimum number of gold coins required for this journey.

## Input Format

The first line contains two positive integers $m$ and $n$, separated by a space, representing the size of the chessboard and the number of colored squares, respectively.

The next $n$ lines each contain three positive integers $x$, $y$, and $c$, representing that the square at coordinates $(x, y)$ has color $c$.

Here, $c=1$ represents yellow, and $c=0$ represents red. Adjacent numbers are separated by a space. The top-left corner of the board is at coordinates $(1, 1)$, and the bottom-right corner is at coordinates $(m, m)$.

All other squares on the board are colorless. It is guaranteed that the top-left corner, i.e., $(1, 1)$, is always colored.

## Output Format

A single integer representing the minimum number of gold coins spent, or `-1` if it is not possible to reach the destination.

## Sample Input and Output

### Sample Input #1

```
5 7
1 1 0
1 2 0
2 2 1
3 3 1
3 4 0
4 4 1
5 5 0
```

### Sample Output #1

```
8
```

### Sample Input #2

```
5 5
1 1 0
1 2 0
2 2 1
3 3 1
5 5 0
```

### Sample Output #2

```
-1
```

## Notes

**Sample 1 Explanation**

The colors of the chessboard are shown in the table below, with blank spaces indicating colorless squares.

| $\color{red}\text{Red}$ | $\color{red}\text{Red}$ |  |  |  |
| :----------: | :----------: | :----------: | :----------: | :----------: |
|  | $\color{yellow}\text{Yellow}$ |  |  |  |
|  |  | $\color{yellow}\text{Yellow}$ | $\color{red}\text{Red}$ |  |
|  |  |  | $\color{yellow}\text{Yellow}$ |  |
|  |  |  |  | $\color{red}\text{Red}$ |

Starting from $(1,1)$, moving to $(1,2)$ does not cost any gold coins.

Moving down from $(1,2)$ to $(2,2)$ costs 1 gold coin.

Casting a spell to change $(2,3)$ to yellow from $(2,2)$ costs 2 gold coins.

Moving from $(2,2)$ to $(2,3)$ does not cost any gold coins.

Moving from $(2,3)$ to $(3,3)$ does not cost any gold coins.

Moving from $(3,3)$ to $(3,4)$ costs 1 gold coin.

Moving from $(3,4)$ to $(4,4)$ costs 1 gold coin.

Casting a spell to change $(4,5)$ to yellow from $(4,4)$ costs 2 gold coins.

Moving from $(4,4)$ to $(4,5)$ does not cost any gold coins.

Moving from $(4,5)$ to $(5,5)$ costs 1 gold coin.

Total cost is 8 gold coins.

**Sample 2 Explanation**

The colors of the chessboard are shown in the table below, with blank spaces indicating colorless squares.

| $\color{red}\text{Red}$ | $\color{red}\text{Red}$ |  |  |  |
| :----------: | :----------: | :----------: | :----------: | :----------: |
|  | $\color{yellow}\text{Yellow}$ |  |  |  |
|  |  | $\color{yellow}\text{Yellow}$ |  |  |
|  |  |  | $\color{white}\text{　}$ |  |
|  |  |  |  | $\color{red}\text{Red}$ |

Moving from $(1,1)$ to $(1,2)$ does not cost any gold coins.

Moving from $(1,2)$ to $(2,2)$ costs 1 gold coin.

Casting a spell to change $(2,3)$ to yellow and moving from $(2,2)$ to $(2,3)$ costs 2 gold coins.

Moving from $(2,3)$ to $(3,3)$ does not cost any gold coins.

From $(3,3)$, you can only cast a spell to reach $(3,2)$, $(2,3)$, $(3,4)$, or $(4,3)$.

None of these points can reach $(5,5)$, so the output is `-1`.

**Data Size and Constraints**

For 30% of the data, $1 ≤ m ≤ 5, 1 ≤ n ≤ 10$.

For 60% of the data, $1 ≤ m ≤ 20, 1 ≤ n ≤ 200$.

For 100% of the data, $1 ≤ m ≤ 100, 1 ≤ n ≤ 1,000$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
