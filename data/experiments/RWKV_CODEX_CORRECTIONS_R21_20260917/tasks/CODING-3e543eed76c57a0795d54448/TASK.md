CowCow has arrived in a country famous for its soda for a trip.

The map of this country includes $n$ cities connected by $n-1$ roads, such that any two cities are connected by a path. The cities produce sodas of various flavors. While traveling on road $i$, CowCow will consume $w_i$ units of soda. CowCow loves drinking soda, but excessive consumption is harmful to health. Therefore, he hopes that during his trip, the average daily soda consumption is as close as possible to a given positive integer $k$.

Additionally, CowCow wants his travel plan to be as interesting as possible. He will choose a starting city and travel to a new city each day via a road, ending his journey in some city.

CowCow is eager to start drinking cola, so he asks you to design a travel plan that minimizes the value of $|P - k|$ (where $P$ is the average daily soda consumption). Please tell him the minimum value, which should be the integer part of this minimum value (i.e., floor the value and output it).

## Input Format

The first line contains two positive integers $n$ and $k$.

The next $n-1$ lines each contain three positive integers $u_i$, $v_i$, and $w_i$, indicating that there is a road of length $w_i$ connecting city $u_i$ and city $v_i$.

Integers on the same line are separated by a single space.

## Output Format

A single line containing an integer, which is the integer part of the minimum value (i.e., the floored value).

## Sample Input and Output

### Sample Input #1

```
5 21
1 2 9
1 3 27
1 4 3
1 5 12
```

### Sample Output #1

```
1
```

## Notes/Hints

### Sample Explanation

In the graph, the path $5 \to 1 \to 3$ is the most suitable route. The total soda consumption is $27 + 12 = 39$, and the average daily soda consumption is $39 \div 2 = 19.5$. The absolute difference from $k$ is $|19.5 - 21| = 1.5$, which, when floored, gives $1$. Thus, the answer is $1$.

### Data Range

For $20\%$ of the data, $n \leq 1000$.

For another $20\%$ of the data, there is an edge connecting node $i$ (for $1 \leq i \leq n-1$) and node $i+1$.

For another $20\%$ of the data, the data forms a complete binary tree with node $1$ as the root (in a complete binary tree, there is a road between node $i$ (for $2 \leq i \leq n$) and node $\lfloor i \div 2 \rfloor$).

For another $20\%$ of the data, all nodes except node $1$ have a road connecting to node $1$.

For $100\%$ of the data, $1 \leq n \leq 5 \times 10^4$, $0 \leq w_i \leq 10^{13}$, $0 \leq k \leq 10^{13}$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
