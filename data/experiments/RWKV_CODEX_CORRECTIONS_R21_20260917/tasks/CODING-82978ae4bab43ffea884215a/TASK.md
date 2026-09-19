Mirko's village is about to hold an exam.

## Problem Description

As the exam approaches, students are stepping up their review pace. Each student has two ability coefficients, $A$ and $B$.

We consider a student will seek help from another student if and only if the other student's $A$ and $B$ are both not less than this student's.

Given $n$ instructions, there are two types:

- `D A B`: A student arrives with ability coefficients $A$ and $B$.
- `P i`: The $i$-th student wants to know whom to ask for help. To avoid overusing resources, if there are multiple candidates, they will first choose the one with the smallest difference in coefficient $B$. If $B$ is the same, they will choose the one with the smallest difference in coefficient $A$.

Student numbers are assigned sequentially starting from 1 as they arrive.

## Input Format

The first line of input contains an integer $n$, the total number of instructions.

The next $n$ lines each contain one instruction, formatted as described in the problem description.

It is guaranteed that no two students have the same coefficients.

## Output Format

For each `P i`, output an integer representing the student number whom the $i$-th student wants to ask for help. If there is no one to ask, output `NE`.

## Sample Input and Output

### Sample Input #1

```
6
D 3 1
D 2 2
D 1 3
P 1
P 2
P 3
```

### Sample Output #1

```
NE
NE
NE
```

### Sample Input #2

```
6
D 8 8
D 2 4
D 5 6
P 2
D 6 2
P 4
```

### Sample Output #2

```
3
1
```

### Sample Input #3

```
7
D 5 2
D 5 3
P 1
D 7 1
D 8 7
P 3
P 2
```

### Sample Output #3

```
2
4
4
```

## Notes

### Data Size and Constraints

For $100\%$ of the data, it is guaranteed that $1 \le n \le 2 \times 10^5$, and $1 \le A, B \le 2 \times 10^9$.

### Translation Note

**This problem is translated from [COCI2006-2007](https://hsin.hr/coci/archive/2006_2007/) [CONTEST #4](https://hsin.hr/coci/archive/2006_2007/contest4_tasks.pdf) *T6 ISPITI***

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
