The task involves a graph with `C` vertices (numbered starting from 1) and `R` edges. This is an undirected graph where each edge has a starting point, an endpoint, a time weight `vi`, and another parameter `ai`. If the parameter `ai` is used on an edge, it can reduce the travel time when traversing that edge, as specified in the problem. You need to determine the minimum time required to travel from vertex 1 to vertex `C`, where you can use the `ai` parameter on only one edge along the path. The time is counted starting when you prepare to leave vertex 1 (You can choose to wait instead of immediately leaving, as shown in example 2). The function mentioned refers to the time elapsed before taking any edge.

## Input and Output Examples

### Input Example #1

```
3 2
1 2 1.5 1.8
2 3 2.0 1.5
2 1
1 2 2.0 1.8
0 0
```

### Output Example #1

```
2.589
1.976
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
