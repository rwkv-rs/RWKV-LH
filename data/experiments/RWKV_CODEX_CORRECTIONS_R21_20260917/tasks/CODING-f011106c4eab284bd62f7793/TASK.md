Given an undirected weighted graph with $n$ vertices and $m$ weighted edges.

Find a matching scheme that maximizes the sum of the weights of the matched edges.

## Input Format

The first line contains two numbers, $n$ and $m$.

The next $m$ lines each contain three numbers: $u$, $v$, and $w$, indicating that there is an edge with weight $w$ between vertex $u$ and vertex $v$.

## Output Format

The first line contains one number, the maximum sum of edge weights.

The next line contains $n$ integers, describing an optimal matching scheme. The $v$-th integer represents the index of the vertex matched with vertex $v$. If vertex $v$ is not matched, output 0.

## Sample Input and Output

### Input Sample #1

```
7 20
5 7 9
3 7 4
3 6 6
2 5 8
5 1 9
1 3 6
6 5 1
2 7 4
2 3 5
6 4 2
7 1 5
5 4 4
4 1 3
5 3 9
7 6 4
2 1 3
4 3 9
6 2 7
4 2 8
6 1 10
```

### Output Sample #1

```
28
6 0 4 3 7 1 5
```

## Notes/Hints

$1 \le n \le 400$, $1 \le m \le 79800$, $1 \le w \le 5 \times 10^8$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
