Mirko is tired of implementing various data structures for different tasks. Therefore, he decided to write an ultimate data structure to manipulate his favorite sequence of numbers.

Help him out!

Mirko will provide you with his sequence and a series of operations you must execute. Each query either asks for information about the sequence or modifies the existing sequence. Below are all possible operation types.

Operation Type | Description | Example
:-:|:-:|:-:
`1 A B X` | Change all elements in the range $[A, B]$ to $X` | $(9, 8, 7, 6, 5, 4, 3, 2, 1) \to 1 3 5 0 \to (9, 8, 0, 0, 0, 4, 3, 2, 1)$
`2 A B X` | Increment each element in the range $[A, B]$ by $(k+1) \times X$ where $k$ is the position relative to $A$ | $(9, 8, 7, 6, 5, 4, 3, 2, 1) \to 2 3 5 2 \to (9, 8, 9, 10, 11, 4, 3, 2, 1)$
`3 C X` | Insert a number $X$ before the $C$-th position | $(9, 8, 7, 6, 5, 4, 3, 2, 1) \to 3 4 100 \to (9, 8, 7, 100, 6, 5, 4, 3, 2, 1)$
`4 A B` | Query the sum of elements in the range $[A, B]$ | $(2, 18, 7, 6, 1, 4, 7, 7, 2) \to 4 6 7 \to result: 11$

## Problem Description

Given a sequence $f$, the following operations are defined.

Let the current length of the sequence be $n$.

Operation Type | Description
:-:|:-:
`1 A B X` | $f_i = X$ for $A \le i \le B$
`2 A B X` | $f_i += (i-A+1) \times X$ for $A \le i \le B$
`3 C X` | Insert $X$ before the $C$-th position, shifting subsequent elements
`4 A B` | Compute the sum $\sum_{i=A}^B f_i$

## Input Format

The first line contains two positive integers $n$ and $Q$, representing the initial length of the sequence and the number of operations, respectively.

The second line contains $n$ non-negative integers representing the initial sequence.

The next $Q$ lines each contain a query as described above.

## Output Format

For each `4` operation, output a line with the result.

## Sample Input and Output

### Input Sample #1

```
5 5
1 2 3 4 5
1 5 5 0
4 4 5
4 5 5
2 1 5 1
4 1 5
```

### Output Sample #1

```
4
0
25
```

### Input Sample #2

```
1 7
100
3 1 17
3 2 27
3 4 37
4 1 1
4 2 2
4 3 3
4 4 4
```

### Output Sample #2

```
17
27
100
37
```

## Notes/Hints

### Data Size and Constraints

Let the current length of the sequence be $t$.

For $100\%$ of the data, $1 \le n, Q \le 1 \times 10^5$, $f_i \le 1 \times 10^5$, $1 \le X \le 100$, $1 \le A \le B \le t$, $1 \le C \le t + 1$.

### Notes

This problem is worth 130 points.

Translated from [COCI2010-2011](https://hsin.hr/coci/archive/2010_2011/) [CONTEST #7](https://hsin.hr/coci/archive/2010_2011/contest7_tasks.pdf) T6 UPIT.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
