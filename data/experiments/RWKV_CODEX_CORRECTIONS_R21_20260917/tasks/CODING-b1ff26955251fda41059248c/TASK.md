The renowned physicist Alfred E. Newman is working on problems involving polynomial multiplication. For example, he might need to calculate
$$
(-x^8y+9x^3-1+y) \cdot (x^5y+1+x^3)
$$
to get the answer
$$
-x^{13}y^2-x^{11}y+8x^8y+9x^6-x^5y+x^5y^2+8x^3+x^3y-1+y
$$
Unfortunately, these problems are so trivial that this great man's mind is always wandering, and he ends up with incorrect answers. As a result, several nuclear warheads he designed detonated prematurely, destroying five major cities and several rainforests. Your task is to write a program to perform such multiplications and save the world.

## Input Format
The input data file will contain pairs of lines, each with at most 80 characters. The last line of the input file contains a `#` as its first character. Each line of input contains a polynomial with no spaces and no explicit power operators. The exponents are positive, non-zero unsigned integers. The coefficients are integers, but can also be negative. The size of exponents and coefficients is less than or equal to $100$. Each term contains at most one $x$ factor and one $y$ factor.

## Output Format
Your program must multiply each pair of polynomials and print each product on a pair of lines, the first line containing all the exponents appropriately aligned with the rest of the information below it. The following rules govern the output format:

1. Terms in the output line must be in descending order of powers of $x$, and for a given power, in ascending order of powers of $y$.

2. Similar terms must be combined into one term. For example, $40x^2y^3-40x^2y^3$ is replaced by $2x^2y^3$.

3. Terms with a coefficient of zero should not be displayed.

4. The coefficient $1$ is omitted except in the case of constant terms.

5. The exponent $1$ is omitted.

6. Factors of $x^0$ and $y^0$ are omitted.

7. There is one space before and after binary signs (i.e., terms connected by '+' or '-') in the output.

8. If the coefficient of the first term is negative, start the first column with a unary minus sign with no intervening space. Otherwise, the coefficient itself starts the first output column.

9. It can be assumed that the output fits in a single line of maximum length 80 characters.

10. There should be no blank lines between the output lines of each pair.

11. The pair of lines representing one product should be of the same length—trailing blanks should appear after the last non-blank character of the shorter line to achieve this.

## Input and Output Example

### Input Example #1

```
-yx8+9x3-1+y
x5y+1+x3
1
1
#
```

### Output Example #1

```
13 2 11
8
6 5
5 2
3 3
-x y - x y + 8x y + 9x - x y + x y + 8x + x y - 1 + y
1
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
