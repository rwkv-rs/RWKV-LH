The input is a string, and the task is to determine whether it is a palindrome and/or a mirrored string. The input string is guaranteed to contain no digit `0`. A palindrome is a string that reads the same forwards and backwards, such as `abba` and `madam`. A mirrored string is a string that looks the same when viewed in a mirror, such as `2S` and `3AIAE`. Note that not every character results in a valid character when mirrored. In this problem, each character and its mirror are defined as follows:

```cpp
Character   Mirror
A           A
E           3
H           H
I           I
J           L
L           J
M           M
O           O
S           2
T           T
U           U
V           V
W           W
X           X
Y           Y
Z           5
1           1
2           S
3           E
5           Z
8           8
```

Each line of input consists of a string (containing only the above characters and no whitespace characters). Determine whether each string is a palindrome, a mirrored string, both, or neither (a total of 4 possible combinations).

## Input and Output Examples

### Sample Input #1

```
NOTAPALINDROME
ISAPALINILAPASI
2A3MEAS
ATOYOTA
```

### Sample Output #1

```
NOTAPALINDROME -- is not a palindrome.

ISAPALINILAPASI -- is a regular palindrome.

2A3MEAS -- is a mirrored string.

ATOYOTA -- is a mirrored palindrome.
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
