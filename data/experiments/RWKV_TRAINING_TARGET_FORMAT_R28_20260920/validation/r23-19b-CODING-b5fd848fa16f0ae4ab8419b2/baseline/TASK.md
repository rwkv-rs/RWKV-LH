Given a tree with $N$ nodes, rooted at $R$, we want to color all the nodes of this tree. The cost to color node $i$ is $t \cdot a_i$, where $t$ represents the number of times coloring has been performed, and $a_i$ is the given weight.

Additionally, **before coloring a node, its parent node must have already been colored** (thus, the root node $R$ must be colored first). Calculate the minimum cost to color the entire tree.

### Input Format

**There are multiple sets of test data for this problem.**

For each set of data, the first line contains two integers $N$ and $R$, representing the number of nodes in the tree and the index of the root node.

The second line contains $N$ integers, where the $i$-th integer represents $a_i$, as described in the problem.

The next $\left(N-1\right)$ lines each contain two integers $u,v$, **indicating that $u$ is the parent of $v$.**

The end of the input is marked by $N=R=0$. **You do not need to process this set of data.**

### Output Format

For each set of data, output a single line containing an integer that represents the minimum cost.

### Constraints and Hints

$1\leq R \leq N\leq 10^3$,
$1\leq a_i\leq 500$.

$\small{\text{Statement fixed by @Starrykiller.}}$

## Sample Input

### Input Example #1

```
5 1
1 2 1 2 4
1 2
1 3
2 4
3 5
0 0
```

### Sample Output #1

```
33
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
