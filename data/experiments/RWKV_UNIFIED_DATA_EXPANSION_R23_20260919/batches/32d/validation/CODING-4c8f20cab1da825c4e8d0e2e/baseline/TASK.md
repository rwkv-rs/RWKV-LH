A simple undirected weighted graph is given. Instead of just finding the minimum spanning tree of this graph, you wish to know how many different minimum spanning trees it has. Two minimum spanning trees are considered different if they have at least one edge that is not the same. Since there may be many different minimum spanning trees, you only need to output the number of such trees modulo $31011$.

## Input Format

The first line contains two numbers, $n$ and $m$, where $1 \le n \le 100$ and $1 \le m \le 1000$, representing the number of nodes and edges in the undirected graph, respectively. Each node is numbered with integers from $1$ to $n$.

The following $m$ lines each contain three integers: $a$, $b$, and $c$, indicating that there is an edge with weight $c$ between nodes $a$ and $b$, where $1 \le c \le 10^9$.

The data guarantees that there are no self-loops or duplicate edges. Note that there are no more than $10$ edges with the same weight.

## Output Format

Output the number of different minimum spanning trees. You only need to output this number modulo $31011$.

## Sample Input and Output

### Input Sample #1

```
4 6
1 2 1
1 3 1
1 4 1
2 3 2
2 4 1
3 4 1
```

### Output Sample #1

```
8
```

## Notes/Hints

### Data Range and Constraints

For all data, $1 \le n \le 100$, $1 \le m \le 1000$, and $1 \le c_i \le 10^9$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
