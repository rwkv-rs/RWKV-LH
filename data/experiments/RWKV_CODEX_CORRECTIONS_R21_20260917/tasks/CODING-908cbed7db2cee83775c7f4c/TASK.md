Xiao W wanted to write a background for a problem about memory, but he forgot.

## Problem Description

There is a bracket string \( S \). Initially, \( S \) contains only a pair of brackets (i.e., the initial \( S \) is `()`). There are \( n \) operations, which are divided into three types:

1. Append a pair of brackets at the end of the current \( S \) (i.e., \( S \) becomes `S()`).
2. Wrap the current \( S \) with a pair of brackets (i.e., \( S \) becomes `(S)`).
3. Cancel the \( x \)-th operation, removing all effects caused by the \( x \)-th operation (e.g., if the \( x \)-th operation was also a cancel operation that canceled the \( y \)-th operation, then the current operation effectively restores the effects of the \( y \)-th operation).

After each operation, you need to output the number of non-empty substrings of \( S \) that are properly matched bracket strings.

A bracket string is properly matched if and only if the number of left and right brackets is equal, and the number of left brackets is not less than the number of right brackets in any prefix.

## Input Format

The first line contains an integer \( n \), the number of operations.

The next \( n \) lines describe each operation. Each line starts with an integer \( op \), indicating the type of operation:

- If \( op = 1 \), it means operation 1 is performed.
- If \( op = 2 \), it means operation 2 is performed.
- If \( op = 3 \), there is an additional integer \( x \), indicating operation 3 is performed, canceling the \( x \)-th operation (operations are numbered from 1 to \( n \), and it is guaranteed that the \( x \)-th operation has occurred). Note that canceling an operation does not affect the numbering of operations, which is determined by the input order.

## Output Format

Output \( n \) lines: the \( i \)-th line should contain an integer \( ans_i \), representing the number of non-empty, properly matched substrings of the bracket string after the \( i \)-th operation.

## Sample Input and Output

### Sample Input #1

```
6
1
2
3 1
1
3 3
3 5
```

### Sample Output #1

```
3
4
2
4
6
4
```

### Sample Input #2

```
10
1
2
2
3 2
1
3 3
3 6
1
2
1
```

### Sample Output #2

```
3
4
5
4
6
6
6
9
10
12
```

## Notes

### Sample 1 Explanation

Let \( S[i,j] \) denote the substring from \( S_i \) to \( S_j \) (indices start from 1).

Initially, \( S \) is `()`, and after each operation:

- After the 1st operation: \( S \) is `()()`, matching substrings are \( S[1,2] \), \( S[1,4] \), and \( S[3,4] \), totaling 3.
- After the 2nd operation: \( S \) is `(()())`, matching substrings are \( S[1,6] \), \( S[2,3] \), \( S[2,5] \), and \( S[4,5] \), totaling 4.
- After the 3rd operation: \( S \) is `(())`, matching substrings are \( S[1,4] \) and \( S[2,3] \), totaling 2.
- After the 4th operation: \( S \) is `(())()`, matching substrings are \( S[1,4] \), \( S[1,6] \), \( S[2,3] \), and \( S[5,6] \), totaling 4.
- After the 5th operation: \( S \) is `(()())()`, matching substrings are \( S[1,6] \), \( S[1,8] \), \( S[2,3] \), \( S[2,5] \), \( S[4,5] \), and \( S[7,8] \), totaling 6.
- After the 6th operation: \( S \) is `(())()`, matching substrings are \( S[1,4] \), \( S[1,6] \), \( S[2,3] \), and \( S[5,6] \), totaling 4.

### Data Range

This problem is bundled test cases.

For all data: \( 1 \leq n \leq 2 \times 10^5 \), \( op \in \{1,2,3\} \), \( 1 \leq x \leq n \), an operation is canceled at most once in form (i.e., all \( x \) are distinct).

| Subtask Number | \( n \leq \) | \( op \in \) | Score |
| :------------: | :----------: | :----------: | :---: |
|    Subtask 1   |    100       | \{1,2,3\}    |  10   |
|    Subtask 2   |    10^3      | \{1,2,3\}    |  10   |
|    Subtask 3   |    10^5      | \{1,2,3\}    |  30   |
|    Subtask 4   | 2 \times 10^5| \{1,2\}      |  20   |
|    Subtask 5   | 2 \times 10^5| \{1,2,3\}    |  30   |

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
