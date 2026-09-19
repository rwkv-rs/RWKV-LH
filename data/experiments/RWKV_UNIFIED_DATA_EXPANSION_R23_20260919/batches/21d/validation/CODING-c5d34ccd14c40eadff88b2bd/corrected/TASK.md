The second challenge is related to the famous Fibonacci sequence, which is well-known among OIers on Earth:
$$F_n = \begin{cases} 1 & (n \le 2) \\ F_{n-1}+F_{n-2} & (n \ge 3) \end{cases}$$
Each term can be referred to as a Fibonacci number.

Given a positive integer $n$, it can be expressed as a sum of some Fibonacci numbers. If we require that different schemes cannot contain the same Fibonacci number, how many schemes can be written for a given $n$?

## Input Format

Only one integer $n$.

## Output Format

An integer representing the number of schemes.

## Sample Input and Output

### Sample Input #1

```
16
```

### Sample Output #1

```
4
```

## Notes

Hint: 16 = 3 + 13 = 3 + 5 + 8 = 1 + 2 + 13 = 1 + 2 + 5 + 8

**Data Range:**
For $30\%$ of the data, $n \le 256$;
For $100\%$ of the data, $n \le 10^{18}$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
