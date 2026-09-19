The Ackermann function is a well-known function. Let's examine how it works:

$$
X_{n+1} = \begin{cases}
   \frac{X_{n}}{2} &\text{if } X_{n}\equiv 0\pmod 2 \\
   3X_{n}+1 &\text{if } X_{n}\equiv 1\pmod 2
\end{cases}
$$

The Ackermann function will recurse starting from $X_{1}$ until it reaches $X_{n}=1$.

Now, input several lines, each with 2 positive integers $l$ and $r$. Note that if $l > r$, you should swap them.

+ Let $\operatorname{max}X_i$ for $l \le i \le r$ be $v$;

+ Let the smallest $i$ satisfying $X_i = v$ and $l \le i \le r$ be $s$.

Please output:

Find the integer $V$ such that the Ackermann function starting at $X_{1}=V$ produces the longest sequence when $V \in [l, r]$. Let this length be denoted as $S$. If there are two or more Ackermann functions of the same length, report the smallest one.

## Input and Output Example

### Input Example #1

```
1 20
35 55
0 0
```

### Output Example #1

```
Between 1 and 20, 18 generates the longest sequence of 20 values.
Between 35 and 55, 54 generates the longest sequence of 112 values.
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
