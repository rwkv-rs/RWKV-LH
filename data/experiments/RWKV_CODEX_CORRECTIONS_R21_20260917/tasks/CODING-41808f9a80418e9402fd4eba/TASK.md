## Problem Description

There is a complete graph with $n$ vertices, numbered from $1$ to $n$.  
The edge connecting vertex $i$ and vertex $j$ has a weight of $(i+j)^k$.  
Define the weight of a tree as the sum of the weights of all its edges.  
Randomly select a spanning tree from all spanning trees of this graph, and find the expected value of its weight.  
The answer needs to be taken modulo $998244353$.

## Input Format

One line containing two positive integers $n$ and $k$.

## Output Format

One line containing an integer representing the result modulo $998244353$.

## Sample Input and Output

### Sample Input #1

```
3 1
```

### Sample Output #1

```
8
```

### Sample Input #2

```
4 3
```

### Sample Output #2

```
450
```

### Sample Input #3

```
1926 817
```

### Sample Output #3

```
984167516
```

### Sample Input #4

```
998244353 1
```

### Sample Output #4

```
998244352
```

## Notes

### Data Range:   
$1 \le n \le 10^{10000}$  
$1 \le k \le 10^7$

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
