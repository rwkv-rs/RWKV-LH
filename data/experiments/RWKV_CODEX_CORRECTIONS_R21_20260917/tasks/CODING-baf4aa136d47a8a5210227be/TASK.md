A cactus graph is an undirected connected graph where each edge can appear in at most one simple cycle. Intuitively, a cactus graph can be understood as a tree that allows the existence of cycles. However, there is a fundamental difference between cactus graphs and trees: a cactus graph can have multiple spanning subgraphs, whereas a tree has only one (itself). The number of spanning subgraphs in a cactus graph is called the "cactus number." Your task is to calculate the "cactus number" of a given graph.

Examples of cactus graphs:

![Cactus Graph Examples](https://cdn.luogu.com.cn/upload/pic/13241.png)

The first graph is a cactus graph. The second graph is not a cactus graph because the edge (2, 3) appears in two different cycles. The third graph is not a cactus graph because it is not a connected graph.

Some terminology explanations:

- **Simple Cycle**: A simple cycle is a path in the graph where the set of edges forms a cycle, and each vertex appears only once in the cycle. For example, in the second graph, there are three simple cycles: (4, 3, 2, 1, 6, 5), (7, 8, 9, 10, 2, 3), and (4, 3, 7, 8, 9, 10, 2, 1, 6, 5).

- **Spanning Subgraph**: A spanning subgraph is a subgraph of the original graph that can have fewer edges but must not break the connectivity of the graph or remove any vertices from the original graph. The concept of "spanning" is similar to the well-known "minimum spanning tree." For the first graph, removing any edge from cycle I or cycle II can form a spanning subgraph, so it has 6 + 4 + 6 × 4 + 1 = 35 spanning subgraphs (note that the graph itself is also a subgraph).

## Input Format

The first line of the input file contains two integers n and m (1 ≤ n ≤ 20000, 0 ≤ m ≤ 1000). n represents the number of vertices in the graph, and the vertices are always numbered from 1 to n.

The next m lines each represent a path in the graph (note: a path here may not necessarily be a cycle). Each line starts with an integer ki (2 ≤ ki ≤ 1000) representing the number of vertices the path passes through, followed by ki numbers between 1 and n, each representing a vertex in the graph. Adjacent vertices define an edge. A path may pass through a vertex multiple times. For example, in the first example, the first path goes from 2 to 3 and then back to 3 from 8, but we guarantee that all edges will appear in some path and will not appear twice in the same path or in two different paths.

## Output Format

Output the "cactus number" of the graph. If it is not a cactus graph, output 0. Note that the final answer may be a very large number.

## Sample Input and Output

### Input Sample #1

```
14 3
9 1 2 3 4 5 6 7 8 3
7 2 9 10 11 12 13 10
2 2 14
```

### Output Sample #1

```
35
```

### Input Sample #2

```
10 2
7 1 2 3 4 5 6 1
6 3 7 8 9 10 2
```

### Output Sample #2

```
0
```

### Input Sample #3

```
5 1
4 1 2 3 4
```

### Output Sample #3

```
0
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
