Given a polynomial $P(x)$ with $n$ terms and values $c, m$, compute $P(c^0), P(c^1), \dots, P(c^{m-1})$. All answers should be modulo $998244353$.

## Input Format

The first line contains three positive integers $n, c, m$.  
The second line contains $n$ non-negative integers $a_0, a_1, \dots, a_{n-1}$, representing the coefficients of $P(x)$ from lowest to highest degree.

## Output Format

Output one line with $m$ positive integers, where the $i$-th number represents $P(c^{i-1})$.

## Sample Input and Output

### Input Sample #1

```
3 3 3
3 3 3
```

### Output Sample #1

```
9 39 273
```

## Notes

For $100\%$ of the data, $1 \le n, m \le 10^6, 0 \le c, a_i < 998244353$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
