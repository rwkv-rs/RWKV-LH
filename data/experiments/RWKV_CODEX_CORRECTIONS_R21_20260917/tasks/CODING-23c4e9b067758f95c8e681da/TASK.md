The 15-puzzle has been around for over 100 years, and even if you're not aware of it by name, you’ve likely seen it.

It consists of 15 sliding tiles with numbers ranging from 1 to 15, all contained within a 4×4 frame, with one tile missing. Let's refer to the missing tile as "x". The goal of the puzzle is to arrange the tiles in the following order:

```
1 2 3 4
5 6 7 8
9 10 11 12
13 14 15 x
```

The only legal move is to swap the "x" with one of the neighboring tiles that shares an edge. For example, the sequence of moves below solves a somewhat scrambled puzzle:

```
(see the original problem for the four illustrations)
```

The letters in the previous line indicate which adjacent block swaps with the 'x' tile at each step; the values 'r', 'l', 'u', and 'd' represent right, left, up, and down respectively. For example, 'r' denotes moving the tile to the right of 'x' into the empty 'x'.

Not all puzzles are solvable; in 1870, a person named Sam Loyd became famous for identifying unsolvable puzzles, frustrating many.

In fact, to turn an ordinary puzzle into an unsolvable one, you only need to swap two tiles (naturally excluding the missing 'x' tile).

In this problem, you will write a program to solve the lesser-known 8-puzzle, which consists of eight tiles.

The moving rules are the same as those for the 15 sliding tiles.

In the 3x3 grid, there are numbers from 1 to 8 and one space. A number adjacent to the space can be moved into the space's position. For a given scrambled state, determine the minimum number of moves required (using 'x' to represent the space).

The target state is:
```
1 2 3
4 5 6
7 8 x
```

A test case includes multiple test data points.

The first line contains an integer n, representing the number of test cases.

The following n lines provide n initial states.

State description method:
```
Original state:

1 2 3
x 4 6
7 5 8

Input description:

1 2 3 x 4 6 7 5 8
```

Please note the output format requires the following:

1. Add an extra blank line after the output of each set of data, except after the last set.

2. If the input puzzle requires no moves to solve, simply output a blank line.

## Input Example #1

```
1
2 3 4 1 5 x 7 6 8
```

## Output Example #1

```
ullddrurdllurdruldr
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
