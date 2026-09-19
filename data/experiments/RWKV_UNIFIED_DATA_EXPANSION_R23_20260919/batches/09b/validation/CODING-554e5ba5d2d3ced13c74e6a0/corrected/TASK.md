Problem Source: SPOJ3105 Mod

## Problem Description

Given \(a, p, b\), find the smallest natural number \(x\) such that \(a^x \equiv b \pmod p\).

## Input Format

Each test file contains multiple sets of test data, with the constraint that \(\sum \sqrt{p} \leq 5 \times 10^6\).

For each set of data, each line contains three positive integers \(a, p, b\).

When \(a = p = b = 0\), it indicates the end of the test data.

## Output Format

For each set of data, output one line.

If there is no solution, output `No Solution`; otherwise, output the smallest natural number solution.

## Sample Input and Output

### Input Sample #1

```
5 58 33
2 4 3
0 0 0
```

### Output Sample #1

```
9
No Solution
```

## Notes

For 100% of the data, \(1 \leq a, p, b \leq 10^9\) or \(a = p = b = 0\).

Updated by [SSerxhs](https://www.luogu.com.cn/user/29826) on May 14, 2021.  
New hack data added on July 1, 2021.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
