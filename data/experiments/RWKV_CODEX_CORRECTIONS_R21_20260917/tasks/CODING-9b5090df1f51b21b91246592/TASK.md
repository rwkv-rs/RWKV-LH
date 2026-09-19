We define the $\operatorname{mex}$ of a set as the smallest non-negative integer not present in the set.

Given a sequence \(a_1, \dots, a_n\), for each \(1 \leq k \leq n\), we define \(b_k\) as follows:

- For all subintervals of \(a\) of length \(k\), determine the $\operatorname{mex}$ of the set formed by these subintervals.
- For all the $\operatorname{mex}$ values obtained, determine the $\operatorname{mex}$ of this set itself, denoted as \(b_k\).

Please compute the sequence \(b\).

## Input Format

The first line contains a positive integer \(n\) (\(1 \leq n \leq 10^5\)).

The second line contains \(n\) integers \(a_1, \dots, a_n\) (\(0 \leq a_i \leq n\)).

## Output Format

Output one line containing \(n\) integers \(b_1, \dots, b_n\).

## Sample Input and Output

### Input Sample #1

```
6
0 0 0 1 2 3
```

### Output Sample #1

```
2 3 4 0 0 0
```

## Notes

### Usage Agreement

This problem is from the THUPC2024 (2024 Tsinghua University Student Programming Contest and University Invitational) Preliminary Round.

The term "this repository" refers to the official repository of the THUPC2024 Preliminary Round ([https://github.com/ckw20/thupc2024_pre_public](https://github.com/ckw20/thupc2024_pre_public)).

1. Any organization or individual may freely use or republish the problems in this repository;
2. Any organization or individual using the problems in this repository should do so without charge and openly, and must not use these problems for profit or add special privileges to these problems;
3. If possible, please provide methods to obtain data, standard programs, and problem solutions when using the problems from this repository; otherwise, please include the GitHub address of this repository.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
