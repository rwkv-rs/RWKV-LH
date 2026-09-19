Given an undirected tree with $n$ nodes, numbered from $1$ to $n$.
Define the distance $\operatorname{d(u,v)}$ between nodes $u$ and $v$ as the sum of the edge weights along the simple path between $u$ and $v$ in the tree.

Given a value $k$, find the $k$-th smallest value among the $\dfrac{n\times (n-1)}{2}$ distances $\operatorname{d(u,v)}$ where $1 \le u < v \le n$.

## Input Format

The first line contains two positive integers $n$ and $k$.

The next $n-1$ lines each contain three positive integers $x, y, z$ (where $1 \le x, y, z \le n$), representing an edge connecting nodes $x$ and $y$ with an edge weight of $n^z$.

## Output Format

Output a single integer, which is the $k$-th smallest value modulo $10^9+7$.

## Sample Input and Output

### Input Sample #1

```
5 8
1 2 1
3 1 3
3 4 1
5 3 2
```

### Output Sample #1

```
135
```

## Notes

For $100\%$ of the data, $2 \le n \le 2.5 \times 10^4$, and $1 \le k \le \dfrac{n \times (n-1)}{2}$.

### Sample Explanation:

All distances $d$ sorted are: $5, 5, 25, 30, 125, 130, 130, 135, 150, 155$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
