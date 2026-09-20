A connected undirected graph is defined as a `Cactus Graph` if no edge is part of more than one simple cycle. Intuitively, a Cactus Graph is a generalization of a tree where some cycles are allowed. Multi-edges (multiple edges between a pair of vertices) and loops (edges that connect a vertex to itself) are not allowed in a Cactus Graph.

Given a Cactus Graph, you can move an edge by removing one edge from the graph and connecting a different pair of vertices with a new edge, such that the resulting graph remains a Cactus Graph. How many ways are there to perform such an edge move?

## Input Format

The first line of the input contains two integers \( n \) and \( m \) ( \( 1 \le n \le 50000 \), \( 0 \le m \le 50000 \) ), representing the number of vertices and edges in the graph, respectively. Vertices are numbered from \( 1 \) to \( n \).

The next \( m \) lines each describe a path in the graph. Each path starts with an integer \( k_i \) ( \( 2 \le k_i \le 1000 \) ) followed by \( k_i \) integers representing the vertices of the path. Adjacent vertices in a path are distinct. A vertex can be visited multiple times in a path, but each edge is traversed exactly once throughout the input.

The graph in the input is guaranteed to be a Cactus Graph.

## Output Format

Output a single integer, which is the number of ways to move an edge in the Cactus Graph.

## Sample Input and Output

### Input Sample #1

```
6 1
7 1 2 5 6 2 3 4
```

### Output Sample #1

```
42
```

### Input Sample #2

```
15 3
9 1 2 3 4 5 6 7 8 3
7 2 9 10 11 12 13 10
5 2 14 9 15 10
```

### Output Sample #2

```
216
```

## Notes/Hints

Time limit: 1 second, Memory limit: 256 MB.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
