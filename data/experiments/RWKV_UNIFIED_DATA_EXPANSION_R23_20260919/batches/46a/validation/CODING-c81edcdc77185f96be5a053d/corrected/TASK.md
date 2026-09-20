### Problem Description

A polynomial equation can be expressed as follows:

$$a_nx^n+a_{n-1}x^{n-1}+\cdots+a_1x^1+a_0=0$$

Here, the unknown is $x$, and $a_n, a_{n-1}, \ldots, a_1, a_0$ are the coefficients. To define a polynomial equation, we only need to specify its coefficients. The roots of the polynomial are the values of $x$, denoted as $z$, for which the polynomial equals zero. You can assume that a polynomial equation of degree $n$ has $n$ distinct roots.

### Input Format

Multiple sets of data. For each set, the first line contains an integer $n$, followed by $(n+1)$ floating-point numbers $a_n, a_{n-1}, \ldots, a_0$, representing the coefficients of the polynomial. Input ends with $n=0$ (make sure to write your program robustly!).

$n \le 5, |a_i| \le 10^9, |z| \le 25$.

### Output Format

For each set of data, output `Equation S` (where $S$ is the equation number), followed by $N$ floating-point numbers, which are the roots of the input equation, sorted in ascending order, rounded to four decimal places.

## Sample Input/Output

### Sample Input #1

```
2 1 -9.5750000000 -179.5585140000
4 1 53.3120000000 958.2510390000 6677.1763593480 15733.6254955064
```

### Sample Output #1

```
Equation 1: -9.4420 19.0170
Equation 2: -22.8060 -18.1170 -6.7350 -5.6540
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
