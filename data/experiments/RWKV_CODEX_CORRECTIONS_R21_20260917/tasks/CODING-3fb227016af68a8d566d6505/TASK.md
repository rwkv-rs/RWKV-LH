You are given an integer sequence \(a\) of length \(n\), and a constant \(c\).

There are \(m\) operations:

- `1 x y`: Modify the value at position \(x\) to \(y\).
- `2 l r`: Query the maximum value of \(\max\left(\max_{l \leq l' \leq r' \leq r \atop r'-l'+1\leq c} \left(\sum_{i=l'}^{r'} a_i\right), 0\right)\) in the interval \([l, r]\).

## Input Format

The first line contains three positive integers \(n, m, c\), representing the length of the sequence, the number of operations, and the given constant, respectively.

The next line contains \(n\) integers \(a_1, \dots, a_n\) representing the sequence \(a\).

The following \(m\) lines, each containing three numbers, describe an operation as described above.

## Output Format

For each query, output one line containing the answer.

## Sample Input and Output

### Input Sample #1

```
5 10 2
0 -5 -3 8 -3
1 5 -1
1 2 3
1 5 -6
1 2 9
2 5 5
2 3 3
1 1 -3
2 4 4
1 1 4
1 3 3
```

### Output Sample #1

```
0
0
8
```

## Notes/Hints

For \(100\%\) of the data, \(1 \le n \le 10^6, 1 \le m \le 2 \times 10^6, 1 \le x, c \le n, 1 \le l \le r \le n, -10^9 \le a_i, y \le 10^9\).

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
