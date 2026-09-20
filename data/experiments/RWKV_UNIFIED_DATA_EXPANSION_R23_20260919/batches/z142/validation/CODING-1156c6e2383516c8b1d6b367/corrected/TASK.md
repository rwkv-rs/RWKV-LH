Let's call a fraction $\frac{x}{y}$ good if there exists at least one another fraction $\frac{x'}{y'}$ such that $\frac{x}{y} = \frac{x'}{y'}$, $1 \le x', y' \le 9$, the digit denoting $x'$ is contained in the decimal representation of $x$, and the digit denoting $y'$ is contained in the decimal representation of $y$. For example, $\frac{26}{13}$ is a good fraction, because $\frac{26}{13} = \frac{2}{1}$. You are given an integer number $n$. Please calculate the number of good fractions $\frac{x}{y}$ such that $1 \le x \le n$ and $1 \le y \le n$. The answer may be really large, so print it modulo $998244353$.

## Time Limit and Memory Limit

Time Limit: 4 seconds
Memory Limit: 512 megabytes

## Input Specification

The only line of the input contains one integer $n$ ($1 \le n < 10^{100}$).

## Output Specification

Print the number of good fractions $\frac{x}{y}$ such that $1 \le x \le n$ and $1 \le y \le n$. The answer may be really large, so print it modulo $998244353$.

## Examples

### Input #1

42


### Output #1

150


### Input #2

3141592653589793238462643383279


### Output #2

459925407

## Note

None

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
