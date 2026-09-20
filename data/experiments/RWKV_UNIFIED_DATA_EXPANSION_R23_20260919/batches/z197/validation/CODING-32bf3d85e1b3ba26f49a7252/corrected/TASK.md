### Problem Description
Given a program control flow graph, from each node to its successor nodes, the probability of transition is equal. When a node without successors is executed, the entire program terminates. The program always starts execution from node number $1$. Given $q$ nodes, calculate the expected number of times each node is executed.

This problem consists of multiple test cases.

### Input Format
For each test case, the input format is as follows:

The first line contains an integer $n$ $(1 \leqslant n \leqslant 100)$, indicating the number of nodes.

The following lines contain two integers $a$, $b$, indicating that $b$ is a successor node of $a$. If $a = b = 0$, this section ends.

The next line contains an integer $q$, which is the number of queries.

The next $q$ lines each contain a single integer, representing the node to be queried.

The end of input is indicated by $n = 0$.

### Output Format
For each query, output the expected number of times the node is executed.

If the program will not terminate, output `infinity`.

## Input and Output Examples

### Input Example #1

```
3
1 2
2 3
2 1
0 0
3
1
2
3
3
1 2
2 3
3 1
0 0
3
3
2
1
0
```

### Output Example #1

```
Case #1:
2.000
2.000
1.000
Case #2:
infinity
infinity
infinity
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
