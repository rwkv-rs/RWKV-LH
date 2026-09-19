Given an integer sequence \(a_1, \dots, a_n\), there are \(m\) operations.

Each operation provides \(l, r, x\). First, a modification is performed, then the query asks how many distinct values are there in \(a_1, \dots, a_x\).

If \(l \le r\), the modification sorts \(a_l, \dots, a_r\) in ascending order; otherwise, it sorts \(a_r, \dots, a_l\) in descending order.

## Input Format

The first line contains two integers \(n, m\).

The second line contains \(n\) integers \(a_1, \dots, a_n\).

The next \(m\) lines, each containing three integers \(l \oplus c, r \oplus c, x \oplus c\), represent the operations sequentially, where \(\oplus\) denotes bitwise XOR, and \(c\) is the answer to the previous query (specifically, for the first operation, \(c = 0\)).

## Output Format

There are \(m\) lines, each containing a single integer, representing the answer to each query in sequence.

## Sample Input and Output

### Input Sample #1

```
9 7
2 2 8 8 2 8 2 1 3
2 2 2
3 7 6
6 7 1
9 6 7
10 11 10
7 0 5
5 1 7
```

### Output Sample #1

```
1
2
1
2
3
2
2
```

## Notes/Hints

Idea: ccz181078, Solution: ccz181078, Code: ccz181078, Data: ccz181078

For \(20\%\) of the data, \(n, m \le 10^3\).

For another \(20\%\) of the data, \(a_i \le 10\).

For another \(20\%\) of the data, \(a_i \le 100\).

For another \(20\%\) of the data, \(n, m \le 10^5\).

For \(100\%\) of the data, \(1 \le a_i \le n\), \(1 \le l, r, x \le n\), \(1 \le n, m \le 10^6\).

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
