Given an integer $x$. Your task is to find out how many positive integers $n$ ($1 \leq n \leq x$) satisfy $n \cdot a^n \equiv b \quad (\textrm{mod}\;p),$ where $a, b, p$ are all known constants.

## Time Limit and Memory Limit

Time Limit: 3 seconds
Memory Limit: 256 megabytes

## Input Specification

The only line contains four integers $a,b,p,x$ ($2 \leq p \leq 10^6+3$, $1 \leq a,b < p$, $1 \leq x \leq 10^{12}$). It is guaranteed that $p$ is a prime.

## Output Specification

Print a single integer: the number of possible answers $n$.

## Examples

### Input #1
2 3 5 8

### Output #1
2

### Input #2
4 6 7 13

### Output #2
1

### Input #3
233 233 10007 1

### Output #3
1

## Note

In the first sample, we can see that $n=2$ and $n=8$ are possible answers.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
