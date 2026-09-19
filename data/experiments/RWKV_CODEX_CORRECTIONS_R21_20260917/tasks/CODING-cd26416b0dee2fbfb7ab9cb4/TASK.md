## Problem Description

Bob loves strings.

Bob considers strings that repeat twice to be beautiful. For example, `aa`, `sese`, `abcabc`, `baabaa`, `abababab` are beautiful strings, while `ab`, `aadead`, `sesese`, `abba` are not. More specifically, if a string \( S \) can be written as the concatenation of two identical strings, i.e., there exists a string \( P \) such that \( S = PP \), then \( S \) is beautiful.

Bob has a string \( T = T_1T_2 \cdots T_n \) of length \( n \). Now he wants to know, given a substring \( Q = T[l \cdots r] \) of \( T \), how many distinct beautiful substrings are contained within \( Q \). If two strings are the same but appear in different positions, they are not considered distinct.

Bob has \( q \) different queries, and you need to quickly compute the answers.

## Input Format

The first line contains two integers \( n \) and \( q \). The second line contains a string \( T \) consisting only of lowercase letters `a` and `b`.

The next \( q \) lines each contain two integers \( l \) and \( r \), representing a query.

## Output Format

Output \( q \) lines, each containing a single integer representing the answer to the corresponding query.

## Sample Input and Output

### Sample Input #1

```
11 5
aabaabaaaab
1 11
1 6
7 10
5 5
3 8
```

### Sample Output #1

```
5
2
2
0
2
```

## Notes

Explanation for Sample #1:

In \( T \), the distinct beautiful substrings are `aa`, `aaaa`, `abaaba`, `aabaab`, `baabaa`.

For the first 10% of the data, \( n \leq 100 \).

For the first 20% of the data, \( n \leq 500 \).

For the first 40% of the data, \( n \leq 5000 \).

For another 20% of the data, the number of beautiful substrings in \( T \) does not exceed \( 10^6 \), considering different positions as different.

For another 20% of the data, \( q = 1 \).

For 100% of the data, \( 1 \leq n, q \leq 200000 \), \( 1 \leq l \leq r \leq n \), and \( T \) consists only of lowercase letters `a` and `b`.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
