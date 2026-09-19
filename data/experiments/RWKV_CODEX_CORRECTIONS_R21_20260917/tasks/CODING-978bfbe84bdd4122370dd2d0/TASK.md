A challenging professor has presented you with the following problem:

$$x_0 = 1$$
$$x_i = x_{\left\lfloor i - \sqrt x \right\rfloor} + x_{\left\lfloor\ln(i)\right\rfloor} + x_{\left\lfloor i\sin^2 (i) \right\rfloor}$$

Calculate the value of $x_i \bmod 10^6$.

## Input Format

The input consists of many integers between $[0, 10^6]$, with each integer on a new line. The input ends with `-1`.

## Output Format

For each input $i$, you should output a single line showing the value of $x_i \bmod 10^6$.

## Sample Input

```
0
-1
```

## Sample Output

```
1
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
