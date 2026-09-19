## Problem Description

Xiao Ben has discovered that for any $n$ letters, their rotation formula can be expressed as a linear combination of $n$ basic rotation formulas.

Basic rotation formulas for:
- One variable: $a$;
- Two variables: $a+b$, $ab$;
- Three variables: $a+b+c$, $ab+ac+bc$, $abc$;
- Four variables: $a+b+c+d$, $ab+ac+ad+bc+bd+cd$, $abc+abd+bcd$, $abcd$;
- ...

Given the values of the basic rotation formulas for $n$ numbers, find the sum of their $m$-th powers, modulo $899678209$ ($899678209 = 429 \times 2^{21} + 1$).

## Input Format

The first line contains two positive integers $n, m$, as described in the problem.  
The next line contains $n$ positive integers, where the $i$-th integer $a_i$ represents the value of the $i$-th basic rotation formula for $n$ variables.

## Output Format

Output a single integer, which is the answer.

## Sample Input and Output

### Sample Input #1

```
2 2
9 18
```

### Sample Output #1

```
45
```

### Sample Input #2

```
9 233333
9 1 8 7 5 6 3 4 2
```

### Sample Output #2

```
100006329
```

## Notes

[Explanation of Sample #1]  
We can set up the equations $a+b = 9$ and $ab = 18$, and easily calculate that $a^2+b^2 = 45$.

[Data Range]  
- For $20\%$ of the data, $1 \le n \le 1000$, $1 \le m \le 10^4$;  
- For $60\%$ of the data, $1 \le n \le 1000$, $1 \le m \le 10^9$;  
- For $100\%$ of the data, $1 \le n \le 3 \times 10^4$, $1 \le m \le 10^9$, $1 \le a_i \le 10^8$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
