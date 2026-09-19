## Problem Description

The problem is as follows:

For any \( n \)-order square matrix, if the sum of the weights at any \( n \) positions selected from different rows and columns is always equal, we call this matrix clever. Note that any matrix for \( n = 1 \) is clever. For example, the matrix:

```cpp
1 2 3
4 5 6
7 8 9
```

is clever because \( 1 + 5 + 9 = 1 + 6 + 8 = 2 + 4 + 9 = 2 + 6 + 7 = 3 + 5 + 7 = 3 + 4 + 8 = 15 \).

However, the matrix:

```cpp
1 2
2 1
```

is not clever because \( 1 + 1 \neq 2 + 2 \).

Now, there is an \( n \times m \) matrix \( M \) and \( T \) queries. Each query asks whether a sub-square matrix is clever.

## Input Format

Input is read from the standard input.

The first line contains three positive integers \( n, m, T \).

The next \( n \) lines each contain \( m \) space-separated non-negative integers, representing matrix \( M \).

The next \( T \) lines each contain three positive integers \( x, y, k \), indicating a query for the \( k \)-order square matrix with the top-left corner at the \( x \)-th row and \( y \)-th column. Ensure that this matrix is completely within \( M \).

## Output Format

Output is written to the standard output.

Output contains \( T \) lines, each with a character 'Y' or 'N'. 'Y' indicates that the queried square matrix is clever, and 'N' indicates it is not.

## Sample Input and Output

### Input Sample #1

```
3 3 4
1 1 1
1 1 1
1 1 2
1 1 2
1 1 3
2 2 2
2 1 2
```

### Output Sample #1

```
Y
N
N
Y
```

## Notes

For all data, \( 0 \leq M_{ij} \leq 10^9 \), \( 1 \leq x \leq n \), \( 1 \leq y \leq m \).

This problem is from the CodePlus December 2017 competition, hosted by the Student Algorithm and Competition Association of the Department of Computer Science and Technology, Tsinghua University.

Credits: Idea/Zhengrong Lu, Problem Setter/Zhengrong Lu, Tester/Shiqing Lyu, Yuzhong Wang

Git Repo: https://git.thusaac.org/publish/CodePlus201712

Thanks to Tencent for supporting this competition.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
