Given a sequence of $k$-order non-singular matrices $a$ over a prime modulus field $p$, and $q$ queries, each providing $l, r$, find $\prod \limits_{i = l}^r a_i$. Here, $p = 1145141$.

Note: A non-singular matrix over the modulus field $p$ means that matrix multiplication and addition are performed modulo $p$, and the determinant of the matrix (in the real number field) modulo $p$ is non-zero.

## Input Format

The first line of input contains three numbers: the length of the matrix sequence $n$, the order of the matrices $k$, and the number of queries $q$.

The next $n \times k$ lines, each containing $k$ integers, represent the $n$ $k$-order matrices, as shown in the sample.

The next $q$ lines, each containing two integers $l, r$, represent a query.

## Output Format

To avoid excessively large output, output a single integer representing the bitwise XOR sum of all elements of the matrices from all queries.

## Sample Input and Output

### Input Sample #1

```
3 3 3
2 2 3
4 5 6
7 8 9
2 2 3
4 5 6
7 8 9
20 20 21
22 23 24
25 26 27
1 2
2 3
1 3
```

### Output Sample #1

```
14921
```

## Notes

### Sample 1 Explanation

$a_1 = \begin{pmatrix} 2 & 2 & 3 \\ 4 & 5 & 6 \\ 7 & 8 & 9\end{pmatrix}$, $a_2 = \begin{pmatrix} 2 & 2 & 3 \\ 4 & 5 & 6 \\ 7 & 8 & 9\end{pmatrix}$, $a_3 = \begin{pmatrix} 20 & 20 & 21 \\ 22 & 23 & 24 \\ 25 & 26 & 27\end{pmatrix}$.

$a_1 \times a_2 = \begin{pmatrix} 33 & 38 & 45 \\ 70 & 81 & 96 \\ 109 & 126 & 150 \end{pmatrix}$, $a_2 \times a_3 = \begin{pmatrix} 159 & 164 & 171 \\ 340 & 351 & 366 \\ 541 & 558 & 582 \end{pmatrix}$, $a_1 \times a_2 \times a_3 = \begin{pmatrix} 2621 & 2704 & 2820 \\ 5582 & 5759 & 6006 \\ 8702 & 8978 & 9363 \end{pmatrix}$.

The bitwise XOR sum of all numbers is $14921$.

### Data Size and Constraints

For all test cases, it is guaranteed that $1 \leq n, q \leq 10^6$, $2 \leq k \leq 3$, $1 \leq l \leq r \leq n$, and all matrix elements are positive integers less than $p$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
