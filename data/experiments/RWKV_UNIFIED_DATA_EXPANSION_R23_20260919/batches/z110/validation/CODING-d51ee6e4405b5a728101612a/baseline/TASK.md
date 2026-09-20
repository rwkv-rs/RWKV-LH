One morning, you think to yourself: "I'm great at programming, why not make some money from it?" So you decide to create a mini-game.

The game is played on a rectangular board divided into w * h square cells. As shown in the example, each square cell can have a game card or be empty. Two game cards are connected if there is a path between them that consists only of horizontal or vertical line segments. The path cannot pass through other game cards, but it is allowed to temporarily leave the rectangular board.

For example: The game cards at (1, 3) and (4, 4) can be connected, while those at (2, 3) and (3, 4) cannot, as every possible path must pass through other game cards.

Your task is to determine if there exists a path that connects the given pair of game cards according to the rules.

### Input

The input consists of multiple test cases. Each test case corresponds to one rectangular board. The first line of each test case contains two integers w and h (1 <= w, h <= 75), representing the width and height of the board, respectively.

The next h lines each contain w characters, representing the distribution of game cards on the board. 'X' indicates a cell contains a game card, while ' ' (a space) indicates an empty cell.

Several subsequent lines each contain four integers x1, y1, x2, y2 (1 <= x1, x2 <= w, 1 <= y1, y2 <= h), specifying the positions of two game cards on the board (note: the top-left corner of the board is coordinate (1, 1)).

It is guaranteed that the positions of the two game cards are not the same. If a line contains four 0s, it denotes the end of the current test case. If a line gives w = h = 0, it indicates the end of all input.

### Output

For each board, output a line "Board #n:", where n is the test case number. Then, for each pair of game cards to be tested, output a line starting with "Pair m: ", where m is the test case number (starting from 1 for each board).

Next, if the cards can be connected, find the path with the minimum number of segments among all possible paths connecting the cards, and output "k segments.", where k is the number of segments in the optimal path. If they cannot be connected, output "impossible.". Output an empty line after each test case.

## Sample Input

```
5 4
XXXXX
X   X
XXX X
 XXX
2 3 5 3
1 3 4 4
2 3 3 4
0 0 0 0
0 0
```

## Sample Output

```
Board #1:
Pair 1: 4 segments.
Pair 2: 3 segments.
Pair 3: impossible.
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
