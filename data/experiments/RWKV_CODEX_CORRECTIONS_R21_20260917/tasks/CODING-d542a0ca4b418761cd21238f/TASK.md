zbw encountered a problem and, in a hurry to meet qby, he wants you to solve it for him.

## Problem Description

Given \( n \) and \( k \), compute the value of the following expression:

\[
\sum_{i=1}^n \sum_{j=1}^n (i+j)^k f(\gcd(i,j)) \gcd(i,j)
\]

where \( \gcd(i,j) \) denotes the greatest common divisor of \( i \) and \( j \).

The function \( f \) is defined as follows:

If \( k \) has a square factor, \( f(k) = 0 \); otherwise, \( f(k) = 1 \).

**Update: A square factor is defined as an integer \( k \) (where \( k > 1 \)) such that \( k^2 \) divides \( n \).**

**Output the answer modulo \( 998244353 \).**

## Input Format

A single line containing two integers \( n \) and \( k \).

## Output Format

A single line containing one integer, representing the answer modulo \( 998244353 \).

## Sample Input and Output

### Sample Input #1

```
3 3
```

### Sample Output #1

```
1216
```

### Sample Input #2

```
2 6
```

### Sample Output #2

```
9714
```

### Sample Input #3

```
18 2
```

### Sample Output #3

```
260108
```

### Sample Input #4

```
143 1
```

### Sample Output #4

```
7648044
```

## Notes

| Test Point | \( n \) | \( k \) |
| :--------: | :-----: | :-----: |
| 1, 2       | \(\leq 10^3\) | \(\leq 10^3\) |
| 3, 4       | \(\leq 2 \times 10^3\) | \(\leq 10^{18}\) |
| 5 – 8      | \(\leq 5 \times 10^4\) | \(\leq 10^{18}\) |
| 9          | \(\leq 5 \times 10^6\) | \(= 1\) |
| 10, 11     | \(\leq 5 \times 10^6\) | \(= 2\) |
| 12, 13     | \(\leq 5 \times 10^6\) | \(\leq 10^3\) |
| 14 – 20    | \(\leq 5 \times 10^6\) | \(\leq 10^{18}\) |

For \( 100\% \) of the data, \( 1 \leq n \leq 5 \times 10^6 \), \( 1 \leq k \leq 10^{18} \).

**Update on 2020/3/16:**

Time limit adjusted to 1 second, which eliminates \( O(n \log k) \) and \( O(n \log \text{mod}) \) approaches.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
