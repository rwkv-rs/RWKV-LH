Given an undirected graph \( G \), where the weight of edge \((A_i, B_i)\) is \( C_i \), determine if the following property holds:

For any cycle \( C \), the XOR sum of the edge weights is 0.

## Input Format

The first line contains an integer \( T \), representing the number of test cases.

For each test case, the first line contains two integers \( N \) and \( M \), representing the number of vertices and edges in graph \( G \), respectively.

The next \( M \) lines contain three integers each, \( A_i \), \( B_i \), and \( C_i \).

## Output Format

For each test case, output one line containing "Yes" or "No".

## Sample Input and Output

### Input Sample #1

```
2
3 3
1 2 1
2 3 2
3 1 3
1 1
1 1 1
```

### Output Sample #1

```
Yes
No
```

## Notes

- For 50% of the data, \( N, M \leq 20 \)
- For 100% of the data, \( 1 \leq N, M \leq 50 \), \( 1 \leq A_i, B_i \leq N \), \( 0 \leq C_i < 2^{16} \)

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
