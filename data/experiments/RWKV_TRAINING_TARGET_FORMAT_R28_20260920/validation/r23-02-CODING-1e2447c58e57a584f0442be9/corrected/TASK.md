The depth, width, and distance between nodes of a binary tree are illustrated as follows:

- Depth: $4$
- Width: $4$
- Distance between nodes 8 and 6: $8$
- Distance between nodes 7 and 6: $3$

The width represents the maximum number of nodes at the same level in the binary tree. The distance between nodes $u$ and $v$ is defined as twice the number of edges directed towards the root plus the number of edges directed towards the leaves on the shortest directed path from $u$ to $v$.

![](https://cdn.luogu.com.cn/upload/pic/6843.png)

Given a binary tree rooted at node 1, you are required to find its depth, width, and the distance between two specified nodes $x$ and $y$.

## Input Format

The first line contains an integer $n$, representing the number of nodes in the tree.  
The next $n - 1$ lines each contain two integers $u$ and $v$, indicating that there is an edge connecting nodes $u$ and $v$.  
The last line contains two integers $x$ and $y$, representing the nodes between which the distance is to be calculated.

## Output Format

Output three lines, each containing one integer, representing the depth, width, and the distance between nodes $x$ and $y$ of the binary tree, respectively.

## Sample Input and Output

### Input Sample #1

```
10                                
1 2                            
1 3                            
2 4
2 5
3 6
3 7
5 8
5 9
6 10
8 6
```

### Output Sample #1

```
4
4
8
```

## Notes

For all test cases, it is guaranteed that $1 \leq u, v, x, y \leq n \leq 100$, and the given structure is a tree. It is also guaranteed that $u$ is the parent node of $v$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
