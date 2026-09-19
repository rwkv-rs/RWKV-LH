For given numbers \( A_1, A_2, \cdots, A_N \), compute the value of

\[
\sum_{i=1}^N \sum_{j=1}^N \mathrm{lcm}(A_i, A_j)
\]

where \(\mathrm{lcm}(a, b)\) denotes the least common multiple of \(a\) and \(b\).

## Input Format

The first line contains an integer \( N \).

The second line contains \( N \) integers \( A_1, A_2, \cdots, A_N \).

## Output Format

Output a single integer, which is the value of the sum.

## Sample Input and Output

### Sample Input #1

```
2
2 3
```

### Sample Output #1

```
17
```

## Notes

For 30% of the test cases, \( 1 \le N \le 1000 \) and \( 1 \le A_i \le 5 \times 10^4 \).

For another 30% of the test cases, \( 1 \le N \le 5 \times 10^4 \) and \( 1 \le A_i \le 1000 \).

For 100% of the test cases, \( 1 \le N \le 5 \times 10^4 \) and \( 1 \le A_i \le 5 \times 10^4 \).

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
