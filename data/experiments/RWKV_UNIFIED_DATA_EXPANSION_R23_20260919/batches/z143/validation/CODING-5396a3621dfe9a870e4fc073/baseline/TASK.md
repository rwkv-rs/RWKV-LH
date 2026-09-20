Define the digit product of a positive integer as the result of multiplying each digit of the number. For example:

The digit product of $2612$ is: $2 \times 6 \times 1 \times 2 = 24$.

Define the self-product of a positive integer as the result of multiplying the number by its digit product. For example:

The self-product of $2612$ is: $2612 \times 24 = 62688$.

Given two integers $A$ and $B$, please find the number of positive integers whose self-product lies within the interval $[A, B]$.

## Input Format

Input consists of two integers $A$ and $B$ on a single line.

## Output Format

Output a single integer, which is the count of positive integers whose self-product is within the interval $[A, B]$.

## Sample Input and Output

### Sample Input #1

```
20 30
```

### Sample Output #1

```
2
```

### Sample Input #2

```
145 192
```

### Sample Output #2

```
4
```

### Sample Input #3

```
2224222 2224222
```

### Sample Output #3

```
1
```

## Notes

### Sample 1 Explanation

There are four positive integers that meet the criteria: $19, 24, 32, 41$. Their self-products are $171, 192, 192, 164$ respectively.

### Data Size and Constraints

- For $25\%$ of the data, $A \le B \le 10^8$;
- For another $15\%$ of the data, $A \le B \le 10^{12}$;
- For $100\%$ of the data, $1 \le A \le B < 10^{18}$.

### Note

**This problem is translated from [COCI2007-2008](https://hsin.hr/coci/archive/2007_2008/) [COI2008](https://hsin.hr/coci/archive/2007_2008/olympiad_tasks.pdf) T4 UMNOZAK**.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
