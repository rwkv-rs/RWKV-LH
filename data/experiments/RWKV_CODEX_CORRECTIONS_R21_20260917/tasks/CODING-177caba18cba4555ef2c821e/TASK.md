After getting tired of solving problems about the longest common substrings and subsequences, you decide to take a different approach.

Here are some definitions:

- A "substring" of a string refers to a continuous segment of the string, for example, `bcd` is a substring of `abcdef`, but `bde` is not.
- A "subsequence" of a string refers to a segment that can be non-continuous, for example, `bde` is a subsequence of `abcdef`, but `bdd` is not.

Given two strings \(a\) and \(b\) consisting of lowercase letters, please calculate:

1. The shortest substring of \(a\) that is not a substring of \(b\).
2. The shortest substring of \(a\) that is not a subsequence of \(b\).
3. The shortest subsequence of \(a\) that is not a substring of \(b\).
4. The shortest subsequence of \(a\) that is not a subsequence of \(b\).

## Input Format

There are two lines, each containing a string consisting of lowercase letters, representing \(a\) and \(b\) respectively.

## Output Format

Output 4 lines, each containing an integer, representing the lengths of the answers to the above 4 questions in order. If there is no valid answer, output `-1`.

## Sample Input and Output

### Sample Input #1

```
aabbcc
abcabc
```

### Sample Output #1

```
2
4
2
4
```

### Sample Input #2

```
aabbcc
aabbcc
```

### Sample Output #2

```
-1
-1
2
-1
```

## Notes

### Data Size and Constraints

- For 20% of the data, the lengths of \(a\) and \(b\) do not exceed 20.
- For 50% of the data, the lengths of \(a\) and \(b\) do not exceed 500.
- For 100% of the data, the lengths of \(a\) and \(b\) do not exceed 2000.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
