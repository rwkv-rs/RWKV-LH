Definition: A $Tour\, belt$ is defined as a subgraph of a given graph where the smallest weight of any edge with both endpoints within this subgraph is strictly greater than the largest weight of any edge with only one endpoint within this subgraph. You are given a graph with $N$ nodes and $M$ edges. Your task is to calculate the sum of the number of nodes in all such $Tour\, belts$ present in the graph.

Input:

The input contains multiple datasets. The first line contains the number of datasets, $T$. For each dataset, the first line contains two integers, $N$ and $M$. The next $M$ lines each contain three integers $a, b, c$, indicating that there is an edge with weight $c$ between nodes $a$ and $b$ in the graph.

Output:

For each dataset, output a single line representing the sum of the number of nodes in all $Tour\, belts$.

Constraints: 

$N \leq 5000$, $M \leq \frac{N(N-1)}{2}$, $c \leq 100000$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
