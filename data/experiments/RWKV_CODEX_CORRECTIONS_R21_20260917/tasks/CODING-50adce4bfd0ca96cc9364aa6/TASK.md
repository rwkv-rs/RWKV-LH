An envelope can hold at most $S$ ($S \le 10$) stamps. There are $N$ sets of stamps ($N \le 10$), each containing no more than $100$ stamps, and each stamp has a certain value. The task is to select a combination of stamps that can form the maximum possible total value. If there are multiple combinations that achieve this maximum, choose the one with the least number of stamps. If there is still a tie, output the combination that is lexicographically smallest when sorted in descending order.

## Input and Output Example

### Input Example #1

```
5
2
4 1 4 12 21
4 1 5 12 28
10
2
5 1 7 16 31 88
5 1 15 52 67 99
6
2
3 1 5 8
4 1 5 7 8
0
```

### Output Example #1

```
max coverage = 71 : 1 4 12 21
max coverage = 409 : 1 7 16 31 88
max coverage = 48 : 1 5 7 8
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
