### Problem Description

Locating a cellphone within a cellular network is a fundamental issue. Assume that the network knows the cellphone is located in one of the $n$ areas: $c_1, c_2, c_3, \ldots, c_n$. The simplest method is to search all these areas simultaneously, but that would waste bandwidth. Since the network can determine the probability of the cellphone appearing in different areas, a compromise is to divide these areas into $w$ groups and access them one group at a time. For example, if a cellphone could be located in 5 areas with probabilities $0.3, 0.05, 0.1, 0.3, 0.25$, one method is to first simultaneously access $\{c_1, c_2, c_3\}$, then access $\{c_4, c_5\}$, where the expected number of regions visited would be $3 \times (0.3 + 0.05 + 0.1) + (3 + 2) \times (0.3 + 0.25) = 4.1$. Another method is to first access $\{c_1, c_4\}$, then $\{c_2, c_3, c_5\}$, where the expected number of regions visited would be $2 \times (0.3 + 0.3) + (3 + 2) \times (0.05 + 0.1 + 0.25) = 3.2$. Your task is to find the minimum expected number of regions that need to be visited.

### Input Format

The first line contains an integer $T$, representing the number of test cases.

For each test case, the first line contains two integers $n, w$. Their meanings are as described above.

The second line of each test case contains $n$ positive integers $u_1, u_2, u_3, \ldots, u_n$. The probability that the cellphone is in area $c_i$ is $p_i = \frac{u_i}{\sum\limits_{j=1}^n u_j}$.

### Output Format

For each test case, output the minimum expected number of regions to be accessed.

### Sample Input

```
2
5 2
30 5 10 30 25
5 5
30 5 10 30 25
```

### Sample Output

```
3.2000
2.3000
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
