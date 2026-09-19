Given two non-negative integers $a, b$ and a positive integer $n(0 \le a, b < 2^{64}, 1 \le n \le 10^3)$, determine the value of $f(a ^ b) \bmod n$, where $f_0 = 0, f_1 = 1$, and $f_{i + 2} = f_i + f_{i + 1}$ for $i \ge 0$.

## Input and Output Examples

### Input Example #1

```
3
1 1 2
2 3 1000
18446744073709551615 18446744073709551615 1000
```

### Output Example #1

```
1
21
250
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
