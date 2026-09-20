If an undirected connected graph has the property that every edge appears in at most one simple cycle, we call this graph a cactus graph. A simple cycle is a cycle that does not repeat any vertex.

![Example Image](https://cdn.luogu.com.cn/upload/pic/13241.png)

For example, the first graph above is a cactus graph, while the second is not—it has three simple cycles: (4, 3, 2, 1, 6, 5, 4), (7, 8, 9, 10, 2, 3, 7), and (4, 3, 7, 8, 9, 10, 2, 1, 6, 5, 4), with edge (2, 3) appearing in the first two cycles. The third graph is not a cactus graph because it is not connected. Clearly, each edge in a cactus graph is either a bridge or appears in exactly one simple cycle. The distance between two points in a graph is defined as the distance of the shortest path between them. The diameter of a graph is defined as the maximum distance between any two points. **Assuming each edge in the cactus graph has a weight of 1, your task is to find the diameter of the given cactus graph.**

## Input Format

The first line of input contains two integers n and m (1 ≤ n ≤ 50000, 0 ≤ m ≤ 10000). n represents the number of vertices, which are numbered from 1 to n. The following m lines represent m paths. Each line starts with an integer k (2 ≤ k ≤ 1000), indicating the number of vertices in the path. This is followed by k integers between 1 and n, each corresponding to a vertex, indicating an edge between adjacent vertices. A path may pass through a vertex multiple times, such as the first example where the path goes from 3 to 8 and back to 3. However, we guarantee that every edge will appear in some path and will not appear in two paths or twice in one path.

## Output Format

Output a single number representing the diameter length of the cactus graph.

## Sample Input and Output

### Input Sample #1

```
15 3
9 1 2 3 4 5 6 7 8 3
7 2 9 10 11 12 13 10
5 2 14 9 15 10
```

### Output Sample #1

```
8
```

### Input Sample #2

```
10 1
10 1 2 3 4 5 6 7 8 9 10
```

### Output Sample #2

```
9
```

## Notes

Explanation for the first sample: The shortest path length between vertex 6 and vertex 12 is 8, so the diameter of this graph is 8.

**Note**: Pascal language users should be aware that their programs may encounter stack overflow when processing large data. If you need to adjust the stack size, you can add a line at the beginning of your program: `{$M 5000000}`, where 5000000 represents the stack size. Please choose an appropriate value based on your program.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
