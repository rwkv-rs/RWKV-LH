You need to solve a problem related to counting double-ended series-parallel circuit diagrams. This is a representation of circuits in topology and graph theory.

A double-ended graph is a series-parallel circuit diagram if and only if it can be represented by the following conditions:

- A single edge is a double-ended series-parallel circuit diagram.
- Connecting the endpoints of double-ended series-parallel circuits together gives us the parallel circuit of these two circuits.
- Connecting one endpoint from each of two circuits gives us the series circuit of these two circuits.

As shown in the problem description in the PDF, the order of the circuit components does not matter. That is, connecting $A, B, C$ in series from left to right is equivalent to connecting $C, A, B$ in the same manner.

Given a number $N(1\leq N \leq30)$, calculate how many different configurations of circuits are possible with $N$ lines.

The answer may not fit within a 32-bit integer range.

**Input Format**

The input contains multiple datasets. Each dataset is on a separate line containing a number $N$. The termination condition is $N=0$.

**Output Format**

For each dataset, output a line containing a single integer, which is the number of configurations possible with the given number of lines.

## Input and Output Example

### Input Example #1

```
1
4
15
0
```

### Output Example #1

```
1
10
1399068
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
