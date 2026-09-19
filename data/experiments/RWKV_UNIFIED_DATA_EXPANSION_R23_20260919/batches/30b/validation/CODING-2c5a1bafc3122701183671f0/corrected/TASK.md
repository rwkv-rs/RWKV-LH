You have a graph with $n$ vertices, and there is an edge between every pair of vertices. Now, after cutting $m$ edges, determine how many different spanning trees are left in the remaining graph.

**Input Format:**

There are multiple test cases, ending with EOF.

For each test case, the first line contains three integers $n$, $m$, $k$, as described above (note: $k$ is actually not used).

The next $m$ lines, each containing two integers $a$, $b$, indicate the edges to be cut from the path from $a$ to $b$.

## Input and Output Example

### Input Example #1

```
5 5 2
3 1
3 4
4 5
1 4
5 3
4 1 1
1 4
3 0 2
```

### Output Example #1

```
3
8
3
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
