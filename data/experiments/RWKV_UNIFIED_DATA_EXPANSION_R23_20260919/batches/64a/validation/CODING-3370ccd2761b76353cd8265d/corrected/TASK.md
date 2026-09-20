Welcome to SAO (Strange and Abnormal Online), a VR MMORPG with n levels. However, the order in which different levels are challenged is a significant issue.

The game has $n-1$ restrictions on challenging levels, such as level $i$ must be challenged before level $j$, or level $k$ must be completed before challenging level $l$. Moreover, without considering the directionality of the restrictions, any two levels are related to some extent under these $n-1$ restrictions. That is, we cannot divide all levels into two non-empty and disjoint subsets such that there are no restrictions between these two subsets.

## Input Format

The first line contains an integer T, representing the number of test cases.

For each test case, the first line contains an integer n, representing the number of levels. The next n - 1 lines each contain "i sign j", where $0 \leq i, j \leq n - 1$ and $i \neq j$, and sign is either "<" or ">", indicating that level $i$ must be completed before/after level $j$.

## Output Format

For each test case, output a single line containing an integer, which is the number of possible sequences to conquer the levels, modulo $1,000,000,007$.

## Sample Input and Output

### Input Sample #1

```
2 
5 
0 < 2 
1 < 2 
2 < 3 
2 < 4 
4 
0 < 1 
0 < 2 
0 < 3
```

### Output Sample #1

```
4 
6
```

## Notes

For $20\%$ of the data, $n \leq 10$.

For $40\%$ of the data, $n \leq 100$.

For another $20\%$ of the data, the sign will only be "<" and $i < j$.

For $100\%$ of the data, $T \leq 5$ and $1 \leq n \leq 1000$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
