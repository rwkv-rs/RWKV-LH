Input an undirected graph with $n$ nodes and a specific node $k$. Output all paths from node $1$ to node $k$, sorted in lexicographical order, where nodes cannot be revisited.

$n \leq 20$.

## Input and Output Example

### Input Example #1

```
6
1 2
1 3
3 4
3 5
4 6
5 6
2 3
2 4
0 0
4
2 3
3 4
5 1
1 6
7 8
8 9
2 5
5 7
3 1
1 8
4 6
6 9
0 0
```

### Output Example #1

```
CASE 1:
1 2 3 4 6
1 2 3 5 6
1 2 4 3 5 6
1 2 4 6
1 3 2 4 6
1 3 4 6
1 3 5 6
There are 7 routes from the firestation to streetcorner 6.
CASE 2:
1 3 2 5 7 8 9 6 4
1 3 4
1 5 2 3 4
1 5 7 8 9 6 4
1 6 4
1 6 9 8 7 5 2 3 4
1 8 7 5 2 3 4
1 8 9 6 4
There are 8 routes from the firestation to streetcorner 4.
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
