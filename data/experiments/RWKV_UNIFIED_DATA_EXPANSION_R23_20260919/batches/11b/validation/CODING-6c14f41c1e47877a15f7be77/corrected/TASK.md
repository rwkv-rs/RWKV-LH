Given $n$ vertices and $m$ edges, with each edge having a specified capacity, find the maximum flow from vertex $s$ to vertex $t$.

**Note that the graph may contain multiple edges between the same pair of vertices.**

## Input Format

The first line contains four integers $n$, $m$, $s$, and $t$.

The following $m$ lines each contain three integers $u$, $v$, and $c$, representing an edge from $u$ to $v$ with a capacity of $c$.

## Output Format

Output a single integer on one line, representing the maximum flow from $s$ to $t$.

## Sample Input and Output

### Input Sample #1

```
7 14 1 7
1 2 5
1 3 6
1 4 5
2 3 2
2 5 3
3 2 2
3 4 3
3 5 3
3 6 7
4 6 5
5 6 1
6 5 1
5 7 8
6 7 7
```

### Output Sample #1

```
14
```

### Input Sample #2

```
10 30 3 7
10 2 18652
8 9 2560
8 9 13734
5 6 23138
9 7 29606
5 8 21673
1 9 11596
3 2 9441
3 7 4829
5 8 24437
1 2 31111
4 10 26213
2 7 31808
1 9 10841
6 8 10758
3 5 11887
4 2 1362
4 1 18182
4 8 18156
10 6 11015
2 7 2640
10 6 27726
10 6 21615
5 1 5959
3 1 19857
5 4 1862
8 9 13830
3 10 22152
4 10 5221
5 2 24065
```

### Output Sample #2

```
68166
```

### Input Sample #3

```
6 18 4 6
4 3 31298
4 5 25605
1 6 8332
1 6 1205
2 3 15950
4 3 1418
1 6 5329
1 6 29907
5 6 22281
1 2 12609
4 1 4033
1 2 12122
4 5 5997
5 6 19507
1 5 19306
2 6 978
5 6 26343
5 3 23224
```

### Output Sample #3

```
35635
```

## Notes

For all data, $1 \le n \le 30$, $1 \le m \le 200$, $0 \le c \le 2^{31} - 1$, and all data are randomly generated.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
