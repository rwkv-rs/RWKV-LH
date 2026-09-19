Company $W$ has $m$ warehouses and $n$ retail stores. The $i$-th warehouse has $a_i$ units of goods; the $j$-th retail store requires $b_j$ units of goods.

The supply and demand of goods are balanced, i.e., $\sum\limits_{i=1}^{m}a_i = \sum\limits_{j=1}^{n}b_j$.

The cost of transporting each unit of goods from the $i$-th warehouse to the $j$-th retail store is $c_{ij}$.

Design a transportation plan to deliver all goods from the warehouses to the retail stores with the minimum total transportation cost.

## Input Format

The first line contains two positive integers $m$ and $n$, representing the number of warehouses and retail stores, respectively.

The next line contains $m$ positive integers $a_i$, indicating the number of units of goods in the $i$-th warehouse.

The following line contains $n$ positive integers $b_j$, indicating the number of units of goods required by the $j$-th retail store.

The next $m$ lines, each containing $n$ integers, represent the cost $c_{ij}$ of transporting each unit of goods from the $i$-th warehouse to the $j$-th retail store.

## Output Format

Output two lines, each containing the minimum and maximum transportation costs, respectively.

## Sample Input and Output

### Input Sample #1

```
2 3
220 280
170 120 210
77 39 105
150 186 122
```

### Output Sample #1

```
48500
69140
```

## Notes/Hints

$1 \leq n, m \leq 100$

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
