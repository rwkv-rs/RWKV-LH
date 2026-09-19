As we all know, a shadow is not an actual object.

## Problem Description

Multiple strings are given, one per line, with an unknown number of strings.

Some strings may be repeated, and we consider that among these strings, those that appear later are the "shadows" of those that appear earlier.

For example,

```plain
abc
def
abc
abc
abc
```

The string `abc` appears on lines $1, 3, 4, 5$. Therefore, the strings on lines $3, 4, 5$ are called "shadow strings".

Now, the task is to concatenate all **non-shadow strings** in the order of their line numbers from smallest to largest into a single long string and output it.

## Input and Output Format

### Input Format

Multiple strings, one per line, as described in the problem.

**Note: The input ends with the string `0` (i.e., a line containing only `0`).**

### Output Format

A single line representing all non-shadow strings concatenated in the order of their line numbers from smallest to largest.

## Sample Input and Output

### Sample Input #1

```
cc
b
a
cc
0
```

### Sample Output #1

```
ccba
```

## Notes

For $20\%$ of the data, there are no repeated strings.

For $100\%$ of the data, $1 \leq n \leq 500$, the total length of the strings does not exceed $50000$, and the character set includes all lowercase letters, digits, `.`, `!`, and `&`.

That is, each string contains only lowercase letters, digits, `.`, `!`, and `&`, with no spaces or special symbols.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
