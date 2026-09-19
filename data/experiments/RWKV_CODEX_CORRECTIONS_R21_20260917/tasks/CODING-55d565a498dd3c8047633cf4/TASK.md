Given a string, count the number of distinct subsequences of it ( including empty subsequence ). For the uninformed, A subsequence of a string is a new string which is formed from the original string by deleting some of the characters without disturbing the relative positions of the remaining characters.   
For example, "AGH" is a subsequence of "ABCDEFGH" while "AHG" is not.

## Input Format

First line of input contains an integer T which is equal to the number of test cases. You are required to process all test cases. Each of next T lines contains a string s.

## Output Format

Output consists of T lines. Ith line in the output corresponds to the number of distinct subsequences of ith input string. Since, this number could be very large, you need to output ans%1000000007 where ans is the number of distinct subsequences.

## Sample Input and Output

### Sample Input #1

```
3
AAA
ABCDEFG
CODECRAFT
```

### Sample Output #1

```
4
128
496
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
