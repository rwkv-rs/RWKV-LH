One day, due to some phenomenon of time travel, you find yourself in the legendary land of the Little People. The layout of this land is quite peculiar. The entire country's transportation system can be seen as a rectangular grid of $2$ rows and $C$ columns, where each point in the grid represents a city. Adjacent cities are connected by roads, resulting in a total of $2C$ cities and $3C-2$ roads.

The traffic in the Little People's country is in a terrible state. Sometimes, due to traffic congestion, the road between two cities becomes disconnected until the congestion is resolved, and the road is restored to normal. As a newcomer, you decide to offer your services to the Ministry of Transportation. The minister, having heard that you come from a technologically advanced world, is overjoyed and asks you to develop a query-response system to save the already dire traffic situation. The Ministry of Transportation will provide you with some traffic information, and your task is to answer queries based on the current traffic conditions. The traffic information can be in the following formats:

- `Close r1 c1 r2 c2`: The road between the adjacent cities $(r_1, c_1)$ and $(r_2, c_2)$ is blocked.
- `Open r1 c1 r2 c2`: The road between the adjacent cities $(r_1, c_1)$ and $(r_2, c_2)$ is cleared.
- `Ask r1 c1 r2 c2`: Query whether the cities $(r_1, c_1)$ and $(r_2, c_2)$ are connected. If there is a path that connects these two cities, return `Y`; otherwise, return `N`.

*Note: $r_i$ represents the row number, $c_i$ represents the column number, and $1 \leq r_i \leq 2, 1 \leq c_i \leq C$.*

## Input Format

The first line contains a single integer $C$, representing the number of columns in the grid. The following lines each contain a piece of traffic information, ending with a single line `Exit`. We assume that all roads are initially blocked. We guarantee that $C$ is less than or equal to $100000$, and the number of information lines is less than or equal to $100000$.

## Output Format

For each query, output a `Y` or `N`.

## Sample Input and Output

### Input Sample #1

```
2
Open 1 1 1 2
Open 1 2 2 2
Ask 1 1 2 2
Ask 2 1 2 2
Exit
```

### Output Sample #1

```
Y
N
```

## Notes

**Data Range:**

For $100\%$ of the data, $1 \leq C \leq 100000$, and $1 \leq$ the number of information lines $\leq 100000$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
