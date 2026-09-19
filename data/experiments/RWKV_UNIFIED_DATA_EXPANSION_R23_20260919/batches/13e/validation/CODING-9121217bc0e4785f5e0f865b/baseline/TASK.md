There are $N$ nodes, and initially, each node does not have a parent node. Your task is to perform $I$ (Insert) operations and $E$ (Evaluate) operations, with formats as follows:  
- $I\ u\ v$: Set node $u$'s parent node to $v$, with a distance of $|u-v| \bmod 1000$. The input guarantees that before executing the instruction, $u$ does not have a parent node.  
- $E\ u$: Query the distance from node $u$ to the root node.

### Input Format

The first line contains the number of test cases $T$. For each test case, the first line contains $n$ $(5\leq n\leq 20000)$. Following are up to $20000$ lines, each containing one instruction, ending with a `0`. The number of $I$ instructions is less than $n$.

### Output Format

For each $E$ instruction, output the query result.

## Input and Output Example

### Input Example #1

```
1
4
E 3
I 3 1
E 3
I 1 2
E 3
I 2 4
E 3
O

```

### Output Example #1

```
0
2
3
5

```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
