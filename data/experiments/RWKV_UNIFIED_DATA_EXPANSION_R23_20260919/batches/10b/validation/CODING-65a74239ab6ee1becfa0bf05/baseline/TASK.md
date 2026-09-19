Generally, a positive integer can be decomposed into the sum of several positive integers.

For example, $1=1$, $10=1+2+3+4$, etc. For a specific decomposition of a positive integer $n$, we call it "excellent" if and only if $n$ is decomposed into several different powers of $2$. Note that a number $x$ can be represented as a power of $2$ if and only if $x$ can be obtained by multiplying several $2$s together.

For example, $10=8+2=2^3+2^1$ is an excellent decomposition. However, $7=4+2+1=2^2+2^1+2^0$ is not an excellent decomposition because $1$ is not a power of $2$.

Now, given a positive integer $n$, you need to determine if there exists an excellent decomposition among all decompositions of this number. If it exists, please provide the specific decomposition.

## Input Format

The input consists of a single line containing an integer $n$, which is the number to be judged.

## Output Format

If there exists an excellent decomposition among all decompositions of the number, then you need to output each number in the decomposition in descending order, separated by a space. It can be proven that, given the order of the decomposition, the solution is unique.

If there is no excellent decomposition, output `-1`.

## Sample Input and Output

### Sample Input #1

```
6
```

### Sample Output #1

```
4 2
```

### Sample Input #2

```
7
```

### Sample Output #2

```
-1
```

## Notes

### Sample 1 Explanation

$6=4+2=2^2+2^1$ is an excellent decomposition. Note that $6=2+2+2$ is not an excellent decomposition because the three numbers in the decomposition are not all distinct.

---

### Data Range and Constraints

- For $20\%$ of the data, $n \le 10$.
- For another $20\%$ of the data, $n$ is guaranteed to be odd.
- For another $20\%$ of the data, $n$ is guaranteed to be a power of $2$.
- For $80\%$ of the data, $n \le 1024$.
- For $100\%$ of the data, $1 \le n \le 10^7$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
