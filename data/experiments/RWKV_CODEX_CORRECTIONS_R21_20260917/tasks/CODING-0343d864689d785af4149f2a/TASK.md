Erast Kopi is a famous Sudoku puzzle designer. The resounding success of his puzzle compilations has led to numerous imitations and plagiarisms. Before filing a lawsuit, he decided to gather more evidence.

A Sudoku puzzle is a $9 \times 9$ table divided into $3 \times 3$ subtables, each containing $3 \times 3$ cells. Each cell may contain a digit from $1$ to $9$. The task is to fill the empty cells such that each row, each column, and each of the $9$ $3 \times 3$ subtables contains each digit from $1$ to $9$ exactly once.

Kopi has a database of Sudoku puzzles and wants to check if it contains similar puzzles. A puzzle $P$ is similar to a puzzle $Q$ if $P$ can be transformed into $Q$ using a sequence of the following operations:

- Choose two digits $x$ and $y$ and replace all $x$ with $y$ and all $y$ with $x$.
- Swap two triples of rows: $(1, 2, 3), (4, 5, 6), (7, 8, 9)$.
- Swap two rows within the same triple of rows.
- Swap two triples of columns: $(1, 2, 3), (4, 5, 6), (7, 8, 9)$.
- Swap two columns within the same triple of columns.
- Flip along the top-left to bottom-right axis. After this operation, columns become rows and vice versa.

Help Kopi find similar puzzles in his database.

## Input Format

The first line of the input contains a single integer $n$ — the number of puzzles in the database ($1 \le n \le 20$).

The rest of the input contains descriptions of $n$ puzzles: $P_1, P_2, \ldots, P_n$. Each puzzle is described by nine lines, each containing nine characters. Each character is either a digit from $1$ to $9$ or a dot ('.'), denoting an empty cell. An empty line separates consecutive puzzles in the database.

There are no spaces in the input file. The puzzles are not guaranteed to be solvable.

## Output Format

Check if puzzle $P_1$ is similar to puzzles $P_2, P_3, \ldots, P_n$, then check if puzzle $P_2$ is similar to puzzles $P_3, P_4, \ldots, P_n$, and so on.

If puzzle $P_i$ is similar to puzzle $P_j$ ($1 \le i < j \le n$), output `Yes`; otherwise, output `No`. If the answer is positive, the next line should contain an integer $q_{ij}$ — the number of operations required to transform puzzle $P_i$ into puzzle $P_j$. The number of operations does not need to be minimal, but it must not exceed $1000$. In the following $q_{ij}$ lines, write the operations that transform puzzle $P_i$ into puzzle $P_j$, one per line.

Operations are encoded as follows:

- `D $x$ $y$` for swapping digits $x$ and $y$.
- `R $a$ $b$` for swapping triples of rows $(3a-2, 3a-1, 3a)$ and $(3b-2, 3b-1, 3b)$.
- `r $a$ $b$` for swapping rows $a$ and $b$, which must belong to the same triple of rows.
- `C $a$ $b$` for swapping triples of columns $(3a-2, 3a-1, 3a)$ and $(3b-2, 3b-1, 3b)$.
- `c $a$ $b$` for swapping columns $a$ and $b$, which must belong to the same triple of columns.
- `F` for flipping along the top-left to bottom-right axis.

The columns are numbered from left to right, and the rows are numbered from top to bottom, starting from one.

## Sample Input and Output

### Input Sample #1

```
4
.....1...
1........
.2.....8.
.........
8....9...
.........
....7....
...2...1.
2...4....

....2....
...7.4...
8.......9
.8...2..1
..2......
.........
.........
..1.8....
.........

1........
.........
.........
.........
.........
.........
.........
.........
.........

.....1...
1........
.2.....8.
.........
8....9...
.........
....7....
...2...1.
2...4....
```

### Output Sample #1

```
Yes
7
C 1 2
D 5 3
F
r 7 9
c 6 5
C 2 3
D 1 8
No
Yes
0
No
Yes
8
R 1 2
C 2 3
c 4 5
F
r 5 6
c 7 9
D 1 8
D 3 5
No
```

## Notes/Hints

Time limit: 2 seconds, Memory limit: 256 MB.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
