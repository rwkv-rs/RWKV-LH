You might be familiar with those puzzles in Sunday magazines: given a sequence of numbers 1, 2, 3, 4, 5, what’s the next number? Sometimes they’re easy to solve, while other times they can be very challenging. Since these “sequence problems” are quite popular, ACM wants to include them in the “Idle Time” section of their new WAP website.

The programmers at ACM noticed that some puzzles can be solved by describing the sequence using a polynomial. For example, the sequence 1, 2, 3, 4, 5 can be easily described by a simple polynomial. The next number would be 6. However, more complex sequences, such as 1, 2, 4, 7, 11, can be described by the polynomial $\frac{1}{2} n^2 - \frac{1}{2}n + 1$. Note that although the numbers in the sequence are integers, the coefficients of the polynomial terms can be any real number.

A polynomial is an expression of the form:

$$P(n) = a_Dn^D + a_{D-1}n^{D-1} + \cdots + a_1n + a_0$$

If $a_D \ne 0$, the number $D$ is called the degree of the polynomial. Note that a constant function $P(n) = C$ could be considered as a polynomial of degree 0, and the zero function $P(n) = 0$ is usually defined as having a degree of -1.

## Input Format

The first line contains an integer $T$, representing the number of test cases.

Each test case includes two lines of input. The first line is two integers separated by a space: $S (1 \le S \le 100)$, and $C (1 \le C \le 100)$, with the condition that $(S + C) \le 100$. The first integer $S$ is the length of the given sequence, and the second integer $C$ is the number of subsequent numbers you need to add after the original sequence.

The second line contains $S$ integers separated by spaces: $X_1, X_2, \cdots, X_S$. These integers form the given sequence. The sequence can be described by a polynomial $P(n)$, meaning for each $i$, $X_i = P(i)$. Among these polynomials, we look for the polynomial with the lowest degree, denoted as $P_{min}$. This polynomial should be used to complete the original sequence.

## Output Format

For each test case, you need to output $C$ integers separated by spaces. These integers are the subsequent numbers calculated using the polynomial with the lowest possible degree. In other words, you need to output $P_{min}(S+1), P_{min}(S+2), \cdots, P_{min}(S+C)$.

It is guaranteed that the values of $P_{min}(S+i)$ are non-negative integers and do not exceed the range of an int.

## Sample #1

### Sample Input #1

```
4
6 3
1 2 3 4 5 6
8 2
1 2 4 7 11 16 22 29
10 2
1 1 1 1 1 1 1 1 1 2
1 10
3
```

### Sample Output #1

```
7 8 9
37 46
11 56
3 3 3 3 3 3 3 3 3 3
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
