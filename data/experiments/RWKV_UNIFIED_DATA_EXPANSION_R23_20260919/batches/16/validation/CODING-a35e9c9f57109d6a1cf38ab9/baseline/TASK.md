In 2016, Sister JiaYuan just learned about trees and was very happy. Now she wants to solve the following problem: Given a rooted tree with the root at node $1$, there are two types of operations:

1. Marking operation: Mark a certain node. (Initially, only node $1$ is marked, and all other nodes are unmarked. A node can be marked multiple times.)

2. Query operation: Query the nearest ancestor of a certain node that has been marked. (The node itself is also considered its own ancestor.)

Can you help her?

## Input Format

The first line contains two positive integers $N$ and $Q$, representing the number of nodes and the number of operations, respectively.

The next $N-1$ lines each contain two positive integers $u, v$ ($1 \leqslant u, v \leqslant n$), indicating that there is a directed edge from $u$ to $v$.

The next $Q$ lines are in the form `oper num`, where `oper` is `C` for a marking operation and `Q` for a query operation.

## Output Format

Output a positive integer representing the result.

## Sample Input and Output

### Input Sample #1

```
5 5
1 2
1 3
2 4
2 5
Q 2
C 2
Q 2
Q 5
Q 3
```

### Output Sample #1

```
1
2
2
1
```

## Notes/Hints

$30\%$ of the data, $1 \leqslant N, Q \leqslant 1000$;

$70\%$ of the data, $1 \leqslant N, Q \leqslant 10000$;

$100\%$ of the data, $1 \leqslant N, Q \leqslant 100000$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
