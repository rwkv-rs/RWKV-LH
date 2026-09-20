There is a tree where you can place device $A$ or device $B$ on each node. Device $A$ can guard all edges adjacent to this node, costing $C_1$ for each. Device $B$ can guard this node and all edges adjacent to it as well as those adjacent to its neighboring nodes, costing $C_2$ for each. (For example, in the graph `1--2--3--4`, placing a $B$ on 1 can guard edges 1-2 and 2-3.) The task is to ensure all edges are guarded and to find the minimum total cost.

## Input and Output Example

### Input Example #1

```
5 30 50
1 2
2 3
3 4
4 5
9 20 30
1 2
2 3
3 4
4 5
4 8
5 6
5 7
8 9
6 100 500
1 3
2 3
3 4
4 5
4 6
0 0 0
```

### Output Example #1

```
50
50
200
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
