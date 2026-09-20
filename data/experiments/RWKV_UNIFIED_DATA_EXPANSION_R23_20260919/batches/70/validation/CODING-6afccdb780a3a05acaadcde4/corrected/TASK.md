Given positive integers \( N \) and integer \( C \), define an \( N \times N \) matrix \( A \) as follows: The element at position \( (i, j) \) (\( 1 \le i \le N \), \( 1 \le j \le N \)) is

- \( 1 \) when \( i = j \),
- \( C \) when \( j \) is not divisible by \( i \),
- \( 0 \) otherwise.

Find the determinant of \( A \) modulo \( 998244353 \) (between \( 0 \) and \( 998244353 - 1 \)).

## Input Format

The input is given from the standard input in the following format:

> \( N \) \( C \)

## Output Format

Output the determinant of \( A \) modulo \( 998244353 \) (between \( 0 \) and \( 998244353 - 1 \)).

## Sample Input and Output

### Sample Input #1

```
6 3
```

### Sample Output #1

```
998244345
```

### Sample Input #2

```
2020 11
```

### Sample Output #2

```
515894850
```

### Sample Input #3

```
1000000000 2020
```

### Sample Output #3

```
4909496
```

## Notes/Hints

### Constraints

- \( 1 \le N \le 10^9 \).
- \( 0 \le C < 998244353 \).

### Partial Points

- If you solve the dataset where \( N \le 10^5 \), you will be awarded \( 20 \) points.
- If you solve the dataset without additional constraints, you will be awarded an additional \( 80 \) points.

### Sample Explanation 1

\( A = \begin{bmatrix}1&0&0&0&0&0\\3&1&3&0&3&0\\3&3&1&3&3&0\\3&3&3&1&3&3\\3&3&3&3&1&3\\3&3&3&3&3&1\end{bmatrix} \), and \( \det A = -8 \).

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
