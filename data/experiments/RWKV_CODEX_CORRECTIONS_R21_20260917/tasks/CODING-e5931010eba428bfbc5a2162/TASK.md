Do you know matrix multiplication?

For two matrices \( A \) and \( B \) of size \( n \times n \), let \( a_{i, j} \) denote the element at the \( i \)-th row and \( j \)-th column of matrix \( A \), similarly for \( B \). If \( C = A \times B \), then \( c_{i, j} = \sum_{k=1}^{n} a_{ik} \times b_{kj} \). Here, \( \sum \) represents the summation symbol, for example, \( \sum_{i=1}^{n} i \) means \( 1 + 2 + \cdots + n \).

## Problem Description

Due to the popularity of the Hobbit, L's roommate X has recently been enthusiastic about studying the currency they use. To conduct his research, X needs to understand something called a bit matrix. Although a bit matrix is also a matrix, its multiplication is slightly different from the usual matrix multiplication.

For a bit matrix \( C = A \times B \), it means \( c_{i,j} = \bigvee_{k=1}^{n} a_{ik} \oplus b_{kj} \). Here, \( \bigvee \) represents the bitwise OR operation over a sequence, for example, \( \bigvee_{i=1}^{n} i \) means \( 1 \mid 2 \mid \cdots \mid n \). The symbol \( \mid \) denotes the bitwise OR operation. The bitwise OR operation means that if at least one of the corresponding bits of two numbers is 1, then the result's bit is 1; otherwise, it is 0. The symbol \( \oplus \) represents the bitwise XOR operation, which means that if the corresponding bits of two binary numbers are different, then the result's bit is 1; otherwise, it is 0.

Here is an example of bit matrix multiplication:

\[
\begin{bmatrix}
1 & 6 \\
3 & 5
\end{bmatrix}
\times
\begin{bmatrix}
3 & 6 \\
5 & 7
\end{bmatrix}
=
\begin{bmatrix}
3 & 7 \\
0 & 7
\end{bmatrix}
\]

Now, X wants you to help him calculate \( A^m \), where \( A \) is an \( n \times n \) bit matrix, and \( A^m \) represents the result of multiplying \( A \) by itself \( m \) times. Formally:

- \( A^1 = A \);
- \( A^m = A^{m-1} \times A \) for \( m > 1 \).

## Input Format

The first line of input contains two positive integers \( n \) and \( m \).

The next \( n \) lines each contain \( n \) non-negative integers. The \( i \)-th line's \( j \)-th number represents the element \( a_{i,j} \) of the bit matrix.

## Output Format

Output the bit matrix \( A^m \) based on the input. Specifically, output the bit matrix in the same format as the input. Refer to the sample output for details.

## Sample Input and Output

### Input Sample #1

```
2 4
10 5
5 10
```

### Output Sample #1

```
0 15
15 0
```

### Input Sample #2

```
3 16
6 5 7
5 6 7
7 7 6
```

### Output Sample #2

```
0 3 3
3 0 3
3 3 0
```

## Notes

### Data Range and Constraints

- For \( 10\% \) of the data, \( n \le 4 \), \( m \le 10000 \).
- For \( 30\% \) of the data, \( n \le 10 \), \( m \le 10^9 \).
- For \( 100\% \) of the data, \( n \le 500 \), \( m \le 10^9 \), all input integers are less than or equal to \( 10^9 \).

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
