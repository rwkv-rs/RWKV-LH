Given a labeled simple undirected connected graph with edge weights all equal to 1, which consists of \( n \) nodes and \( m \) edges. It is known that the shortest path lengths from node 1 to all other nodes are given. Determine the number of possible configurations of this graph.

Specifically, we consider the shortest path from node 1 to itself to be 0.

Two graphs are considered different if and only if there exists at least one edge \((u, v)\) that appears in one graph and not in the other.

**Since little_sun is too powerful, the data guarantees that at least one graph satisfying the conditions exists.**

The answer should be taken modulo \( 998244353 \).

## Input Format

The first line contains two positive integers \( n \) and \( m \) — \( n \) represents the number of nodes in the graph, and \( m \) represents the number of edges.

The second line contains \( n \) non-negative integers \( d_1, d_2, \cdots, d_n \) representing the shortest path lengths from node 1 to the other nodes.

## Output Format

Output a single integer representing your answer.

## Sample Input and Output

### Sample Input #1

```
4 3
0 1 1 2
```

### Sample Output #1

```
2
```

### Sample Input #2

```
5 5
0 1 1 2 2
```

### Sample Output #2

```
12
```

### Sample Input #3

```
8 12
0 2 2 2 2 1 1 1
```

### Sample Output #3

```
128601
```

## Notes

### Sample Explanation

For the first sample, there are two configurations: \(\{(1,2),(1,3),(2,4)\}\) and \(\{(1,2),(1,3),(3,4)\}\).

For the second sample, I have a wonderful explanation, but the space here is too small to write it down.

### Data Range

**This problem uses subtask testing.**

- Subtask 1 (10 pts), \( n \le 7 \), \( m \le 14 \), time limit 1s;
- Subtask 2 (20 pts), \( n \le 50 \), \( m \le 600 \), time limit 1s;
- Subtask 3 (20 pts), \( n \le 1000 \), \( m \le 5000 \), time limit 1s;
- Subtask 4 (50 pts), no special restrictions, time limit 3s.

For \( 100\% \) of the data, \( n \le 10^5 \), \( m \le 2 \times 10^5 \). Let \( t_i = \sum_j [d_j = i] \), it should also satisfy \( \sum_{i} t_i t_{i-1} \le 2 \times 10^5 \).

**This problem enforces O2 optimization.**

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
