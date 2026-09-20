There is an unweighted tree with $n (n \leq 50)$ leaf nodes. Given the pairwise distances between these leaf nodes, reconstruct the tree and output the degree of each non-leaf node.

## Input Format
The input contains multiple datasets.

The first line of each dataset contains an integer $n$.  
The next $n$ lines each contain $n$ integers, where $a_{ij}$ represents the distance between node $i$ and node $j$.

The input ends when $n=0$.

## Output Format
For each dataset, output the solution on one line.

## Sample Input
```
4
0 2 2 2
2 0 2 2
2 2 0 2
2 2 2 0
4
0 2 4 4
2 0 4 4
4 4 0 2
4 4 2 0
2
0 12
12 0
0
```

## Sample Output
```
4
2 3 3
2 2 2 2 2 2 2 2 2 2 2
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
