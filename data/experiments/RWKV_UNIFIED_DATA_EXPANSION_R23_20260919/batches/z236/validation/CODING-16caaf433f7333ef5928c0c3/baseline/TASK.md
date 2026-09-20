The expression on the right side of $F'(x)$ in the problem can be replaced with others, but here it is fixed for ease of testing.

## Problem Description

Given polynomials $F(x), A(x), B(x)$, satisfying:

$$\frac{dF(x)}{dx} \equiv A(x)e^{F(x)-1} + B(x) \pmod{x^n}$$
with $F(0) = 1$.

Given $A(x)$ and $B(x)$, find the first $n$ coefficients of $F(x)$.

The answer should be modulo $998244353$.

## Input Format

The first line contains a positive integer $n$, representing the degree of $A(x)$ and $B(x)$.  
The second line contains $n+1$ integers, from low to high, representing the coefficients of $A(x)$.  
The third line contains $n+1$ integers, from low to high, representing the coefficients of $B(x)$.

## Output Format

Output one line with $n+1$ integers, from low to high, representing the coefficients of $F(x)$.

## Sample Input and Output

### Input Sample #1

```
9
2 9 8 7 3 6 5 4 1 12
23 9 8 7 4 6 1 3 2 5
```

### Output Sample #1

```
1 25 34 332748429 124783260 22560 624092696 904826719 284383572 50973515
```

## Notes

### Data Range and Constraints
For $30\%$ of the data, $1 \le n \le 5000$;  
For $100\%$ of the data, $1 \le n \le 10^5$.

All inputs are guaranteed to be within the range $[0, 998244353)$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
