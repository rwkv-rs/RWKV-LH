There is a grid with $r$ rows and $c$ columns $(1<r,c<10)$, where black cells are represented by `*`, and each white cell contains a letter. A white cell is called a starting cell if there is no white cell to its immediate left or above it (this might be a black cell or an edge of the grid).

Your task is to identify all horizontal words (`Across`). These words must start from a starting cell (a cell where the left is either a black cell or the first column) and extend to the left of a black cell or the far-right column of the grid. Then, identify all vertical words (`Down`), following similar rules: these words must begin from a starting cell (where above is either a black cell or the first row) and extend to the top of a black cell or the bottommost row of the grid.

**[Input Format]**

There are multiple matrix inputs. For the $i$-th matrix, the first line contains $r_i$ and $c_i$ separated by a space $(1<r_i,c_i<10)$, indicating the grid has $r_i$ rows and $c_i$ columns. Below, the content of the matrix follows, consisting of uppercase letters or a `*`. The input sequence is terminated by `0`, which indicates the end of all matrix inputs.

**[Output Format]**

The output for each puzzle includes a puzzle identifier (e.g., `puzzle #1:`) and a list of horizontal and vertical words. For each word, output one word per line, preceded by a number showing its sequence in increasing order as per its position in the grid.

The number should take up three spaces and be right-aligned.

The horizontal word list's heading is `Across`, and the vertical word list's heading is `Down`.

Even if the grid contains only black cells, the `Across` and `Down` headings should still appear.

## Sample Input/Output

### Sample Input #1

```
2 2
AT
*O
6 7
AIM*DEN
*ME*ONE
UPON*TO
SO*ERIN
*SA*OR*
IES*DEA
0
```

### Sample Output #1

```
puzzle #1:
Across
1.AT
3.O
Down
1.A
2.TO
puzzle #2:
Across
1.AIM
4.DEN
7.ME
8.ONE
9.UPON
11.TO
12.SO
13.ERIN
15.SA
17.OR
18.IES
19.DEA
Down
1.A
2.IMPOSE
3.MEO
4.DO
5.ENTIRE
6.NEON
9.US
10.NE
14.ROD
16.AS
18.I
20.A
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
