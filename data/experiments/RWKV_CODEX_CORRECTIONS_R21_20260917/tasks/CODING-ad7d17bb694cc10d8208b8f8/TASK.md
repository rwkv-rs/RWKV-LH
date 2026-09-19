shoi2013d1t2

(This problem is sensitive to constants, be cautious)

## Problem Description

Given a string \( S \) composed of the first \( n \) lowercase letters. The string \( S \) is a factorial string if and only if all permutations (a total of \( n! \) permutations) of the first \( n \) lowercase letters appear as subsequences (not necessarily contiguous) in \( S \).

From this definition, one can derive a simple enumeration method to verify, but it is too slow. Therefore, you are asked to design an algorithm that can determine within 1 second whether a given string is a factorial string.

## Input Format

The first line of input contains an integer \( T \), indicating that there are \( T \) sets of data in the file.

The following are \( T \) blocks, each consisting of 2 lines:

- The first line contains a positive integer \( n \), indicating that \( S \) is composed of the first \( n \) lowercase letters.
- The second line contains a string \( s \).

## Output Format

For each set of data, output one line. Each line should be either `YES` or `NO`, indicating whether the corresponding string \( S \) is a factorial string.

## Sample Input and Output

### Input Example #1

```
2
2
bbaa
2
aba
```

### Output Example #1

```
NO
YES
```

## Notes

In the first set of data, the string `ab` does not appear as a subsequence.

![](https://cdn.luogu.com.cn/upload/image_hosting/9zs871wl.png)

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
