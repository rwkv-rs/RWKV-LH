Xiao L is a severe obsessive-compulsive disorder patient.

Due to his severe obsessive-compulsive disorder, he always draws points on a circle when he draws diagrams.

## Problem Description

One day, he asked Xiao H and Xiao W the following question:

If there are $n$ different points on a circle, numbered from $1$ to $n$, how many ways are there to connect them into a tree?

Xiao H & Xiao W: Isn't this an easy question?

Xiao L: What if the edges cannot intersect?

Xiao H & Xiao W: Isn't this an easy question?

Xiao L: What if we replace "tree" with "graph"?

Xiao H & Xiao W: Isn't this an easy question?

Xiao L: What if each point has a weight $a_i$, and the edge connecting $(i,j)$ has a weight of $a_i \times a_j$, and we need to find the expected sum of all edge weights for a graph that satisfies the above conditions?

Xiao H & Xiao W: Isn't this an easy question?

Xiao L was very frustrated to see his painstakingly crafted problem easily solved by the dalaos. To comfort him, you need to help him solve this problem.

**Note**:
1. Two edges are **not considered intersecting** at their endpoints.
1. A graph with **no edges (i.e., only $n$ points with no edges connecting them) is also valid**.
1. Points are numbered **clockwise from $1$ to $n$**.
1. The graph **cannot have self-loops or multiple edges**.

## Input Format

The first line contains a positive integer $n$, as described above.

The next line contains $n$ non-negative integers, where the $i$-th number is $a_i$, representing the weight of the $i$-th point.

## Output Format

A positive integer representing the result, modulo $998244353$.

## Sample Input and Output

### Sample Input #1

```
4
1 1 1 1
```

### Sample Output #1

```
665496238
```

### Sample Input #2

```
13
1 1 4 5 1 4 1 9 1 9 8 1 0
```

### Sample Output #2

```
748867567
```

## Notes

For the first sample, all $64$ graphs are as follows:
![](https://cdn.luogu.com.cn/upload/image_hosting/zfa8hs0v.png)

Among them, the left $48$ graphs are valid, and the right $16$ graphs are invalid, with all edge weights being $1$.

The expected sum of edge weights is $\dfrac{8}{3}$, and the result under modulo $998244353$ is $665496238$.

### Data Range

**This problem uses subtask testing.**

- Subtask 1 ($10\%$): $n \leq 6$.
- Subtask 2 ($30\%$): $n \leq 3000$.
- Subtask 3 ($60\%$): No special restrictions.

For $100\%$ of the data, $2 \leq n \leq 10^5, 0 \leq a_i \leq 10^6$.

Subtask 1 and Subtask 2 have a time limit of $1$ second, and Subtask 3 has a time limit of $2$ seconds.

------------
If you do not know how to take the modulo of a rational number, please search for "multiplicative inverse" on your own.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
