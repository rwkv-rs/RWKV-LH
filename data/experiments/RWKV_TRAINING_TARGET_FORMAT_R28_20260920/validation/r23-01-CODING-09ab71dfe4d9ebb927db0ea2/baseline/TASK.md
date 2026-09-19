Given a sequence of n numbers a $ _{1} $ , a $ _{2} $ , ..., a $ _{n} $ and a number of k- queries. A k-query is a triple (i, j, k) (1 ≤ i ≤ j ≤ n). For each k-query (i, j, k), you have to return the number of elements greater than k in the subsequence a $ _{i} $ , a $ _{i+1} $ , ..., a $ _{j} $ .

## Input Format

- Line 1: n (1 ≤ n ≤ 30000).
- Line 2: n numbers a $ _{1} $ , a $ _{2} $ , ..., a $ _{n} $ (1 ≤ a $ _{i} $ ≤ 10 $ ^{9} $ ).
- Line 3: q (1 ≤ q ≤ 200000), the number of k- queries.
- In the next q lines, each line contains 3 numbers i, j, k representing a k-query (1 ≤ i ≤ j ≤ n, 1 ≤ k ≤ 10 $ ^{9} $ ).

## Output Format

- For each k-query (i, j, k), print the number of elements greater than k in the subsequence a $ _{i} $ , a $ _{i+1} $ , ..., a $ _{j} $ in a single line.

## Sample Input and Output

### Sample Input #1

```
5
5 1 2 3 4
3
2 4 1
4 4 4
1 5 2
```

### Sample Output #1

```
2
0
3
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
