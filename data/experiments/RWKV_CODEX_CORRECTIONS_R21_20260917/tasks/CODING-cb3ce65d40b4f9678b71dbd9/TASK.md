Given a sequence of non-negative integers \(a_1, a_2, a_3, \ldots, a_n\) of length \(n\), and \(q\) operations, each operation starts with a parameter \(op\):

- If \(op = 0\), two parameters \(x\) and \(y\) follow, which means to change \(a_x\) to \(y\).

- If \(op = 1\), four parameters \(l_1, r_1, l_2, r_2\) follow (guaranteed that \(r_1 - l_1 = r_2 - l_2\)), you need to determine if the intervals \([l_1, r_1]\) and \([l_2, r_2]\) are essentially the same. If they are, output `YES`; otherwise, output `NO`.

The definition of being essentially the same: Let the length of the interval be \(\text{len}\), the sequence \(p_1 \dots p_{\text{len}}\) is the result of sorting \(a_{l_1} \dots a_{r_1}\) in ascending order, and the sequence \(q_1 \dots q_{\text{len}}\) is the result of sorting \(a_{l_2} \dots a_{r_2}\) in ascending order. There exists an integer \(k\) such that \(\forall i, p_i + k = q_i\).

## Input Format

The first line contains two positive integers \(n\) and \(q\), representing the length of the sequence and the number of operations, respectively.

The second line contains \(n\) non-negative integers representing \(a_1, a_2, a_3, \ldots, a_n\).

The following \(q\) lines each represent one of the operations described above.

## Output Format

For operations where \(op = 1\), output whether the two intervals are essentially the same. If they are, output `YES`; otherwise, output `NO`.

## Sample Input and Output

### Input Sample #1

```
12 6
1 1 4 5 1 4 2 2 5 2 3 3
1 1 3 7 9
1 2 3 5 6
1 1 3 2 4
0 7 1
1 1 4 2 5
1 5 7 8 10
```

### Output Sample #1

```
YES
YES
NO
YES
YES
```

## Notes

- Subtask1 ($25$ pts): \(1 \leq n, q \leq 1000\).

- Subtask2 ($25$ pts): \(1 \leq n, q \leq 10^5\), \(0 \leq a_i, y \leq 100\).

- Subtask3 ($25$ pts): \(1 \leq n, q \leq 10^5\).

- Subtask4 ($25$ pts): No additional constraints.

You must pass all test cases in a subtask to earn the points for that subtask.

For all data, the following constraints apply: \(1 \leq n, q \leq 10^6\), \(1 \leq x \leq n\), \(0 \leq a_i, y \leq 10^6\). For all \(l, r\), \(1 \leq l \leq r \leq n\).

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
