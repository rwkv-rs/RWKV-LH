Given \( l, r, k \), compute:
\[
\sum_{i=l}^r \prod_{j=i}^{i+k-1} f_j
\]
where \( f_0 = 0 \), \( f_1 = 1 \), and \( f_n = f_{n-1} + f_{n-2} \) for \( n \geq 2 \). As a conscientious (truly) problem setter, you only need to output the answer modulo \( 998244353 \).

## Input Format

Input consists of three positive integers \( l, r, k \) on a single line.

## Output Format

Output a single integer, which is the answer.

## Sample Input and Output

### Sample Input #1

```
233 888 251
```

### Sample Output #1

```
60539267
```

### Sample Input #2

```
11451 45149 8100
```

### Sample Output #2

```
728539702
```

### Sample Input #3

```
114514 233333 101010
```

### Sample Output #3

```
830578369
```

### Sample Input #4

```
198245 285628 157293
```

### Sample Output #4

```
121742791
```

## Notes

### Data Range

- For 30% of the data, \( 1 \le k \le 1000 \).
- For 70% of the data, \( 1 \le k \le 10^5 \).
- For 100% of the data, \( 1 \le k \le 5 \times 10^5 \), \( 1 \le l \le r \le 10^{18} \).

**Please consider constant optimization.**

Since extending \( l, r \) to high precision range does not make much sense, it is limited to \( 10^{18} \) here.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
