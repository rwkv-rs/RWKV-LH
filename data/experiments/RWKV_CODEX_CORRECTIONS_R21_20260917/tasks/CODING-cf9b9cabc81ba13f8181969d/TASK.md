## Problem Description

Given a positive integer \( n \), determine how many strings of length \( n \) are "program fragments".

The definitions are as follows:

- A single semicolon `;` is a "statement".
- An empty string is a "program fragment".
- If string `A` is a "program fragment" and string `B` is a "statement", then `AB` is a "program fragment".
- If string `A` is a "program fragment", then `{A}` is a "statement block".
- If string `A` is a "statement block", then `A` is a "statement", and `[]A` and `[]()A` are both "functions".
- If string `A` is a "function", then `(A)` is a "function", and both `A` and `A()` are "values".
- If string `A` is a "value", then `(A)` is a "value", and `A;` is a "statement".

**Note: `A` being `B` does not imply `B` is `A`.**

## Input Format

Input consists of a single line containing a positive integer \( n \).

## Output Format

Output a single integer representing the answer, modulo \( 998244353 \).

## Sample Input and Output

### Sample Input #1

```
4
```

### Sample Output #1

```
9
```

### Sample Input #2

```
7
```

### Sample Output #2

```
140
```

### Sample Input #3

```
8923
```

### Sample Output #3

```
424180943
```

### Sample Input #4

```
114514
```

### Sample Output #4

```
552971057
```

## Notes

### Sample 1 Explanation

Valid "program fragments" include: `;;;;`, `;;{}`, `;{;}`, `;{};`, `{;;}`, `{;};`, `{{}}`, `{};;`, `{}{}`.

### Data Range

- For 30% of the data, \( 1 \le n \le 10^5 \).
- For 100% of the data, \( 1 \le n \le 10^7 \).

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
