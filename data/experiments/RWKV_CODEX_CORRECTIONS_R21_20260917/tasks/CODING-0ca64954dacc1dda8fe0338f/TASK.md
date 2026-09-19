A repeating string is a string that can be represented in the form $ A + A $ where $ A $ is a non-empty string. In linguistics, it is also known as a reduplicated word. Japanese has a very high frequency of reduplicated words, which often appear in regular sentences. This time, we want to count them.

You are given a string $ S $ consisting of lowercase alphabets and $ Q $ queries $ [a_i, b_i] $. For each query, find the sum of the lengths of all non-empty substrings of $ S[a_i, b_i] $ that are repeating strings. Note that if the same string exists multiple times, they should be considered as separate instances.

For strings $ A $ and $ B $, the concatenation is represented as $ A + B $. Also, $ S[x, y] $ denotes the substring of $ S $ from the $ x $-th character to the $ y $-th character.

## Input Format

The input is given from the standard input in the following format:

> $ S $ $ Q $ $ a_1 $ $ b_1 $ ... $ a_Q $ $ b_Q $

- The first line contains the string $ S\ (1\ ≦\ |S|\ ≦\ 100000) $. ($ |S| $ denotes the length of the string $ S $)
- The second line contains an integer $ Q\ (1\ ≦\ Q\ ≦\ 100000) $, representing the number of queries.
- The next $ Q $ lines contain the query information. The $ i $-th line ($ 1\ ≦\ i\ ≦\ Q $) contains two integers $ a_i,\ b_i\ (1\ ≦\ a_i\ ≦\ b_i\ ≦\ |S|) $, representing the $ i $-th query, separated by a space.

## Output Format

Output the answer for each query on a new line, totaling $ Q $ lines. Ensure a newline at the end of the output.

## Sample Input and Output

### Sample Input #1

```
kokoropyonpyon
3
1 14
2 14
1 13
```

### Sample Output #1

```
12
8
4
```

### Sample Input #2

```
rattatta
5
2 7
3 8
3 4
3 3
1 8
```

### Sample Output #2

```
10
10
2
0
16
```

### Sample Input #3

```
aaaaaaaaaa
1
1 10
```

### Sample Output #3

```
110
```

## Notes/Hints

### Partial Points

- If you correctly solve all test cases where $ 1\ ≦\ |S|\ ≦\ 1000 $, you will be awarded 100 points as partial credit.
- If you correctly solve all test cases where $ 1\ ≦\ |S|\ ≦\ 20000 $, you will be awarded an additional 100 points as partial credit.
- Correctly solving all test cases will award an additional 150 points.

### Sample Explanation 1

`koko` and `pyonpyon` are the repeating strings. For the first query, considering `kokoropyonpyon`, there are two repeating strings: `koko` and `pyonpyon`, so the answer is 12. For the second query, considering `okoropyonpyon`, there is one repeating string: `pyonpyon`, so the answer is 8. For the third query, considering `kokoropyonpyo`, there is one repeating string: `koko`, so the answer is 4.

### Sample Explanation 2

`attatt`, `ttatta`, `tt`, `tt` are the repeating strings. Note that the two `tt`s are considered separate.

### Sample Explanation 3

Be aware that there can be a large number of repeating strings in some cases.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
