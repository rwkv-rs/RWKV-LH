Initially, there are $k$ creatures of a kind that live for one day. At the end of their life, each creature has a probability $p_i$ of generating $i$ new creatures of the same kind (which also live for only one day). The task is to find the probability that all creatures are dead within $m$ days (including the possibility of dying before $m$ days).

### Input Format

The first line contains an integer $T$, representing the number of test cases.

For each test case, the input begins with three integers $n(1<=n<=1000), k(0<=k<=1000), m(0<=m<=1000)$.

This is followed by $n$ lines, each containing a real number, representing probabilities $p_0$ to $p_{n-1}$.

### Output Format

For each test case, output "Case #x: " (where x is the test case number), followed by the calculated probability. The answer should be rounded to seven decimal places (1e-6 precision).

### Sample Input

```
4
3 1 1
0.33
0.34
0.33
3 1 2
0.33
0.34
0.33
3 1 2
0.5
0.0
0.5
4 2 2
0.5
0.0
0.0
0.5
```

### Sample Output

```
Case #1: 0.3300000
Case #2: 0.4781370
Case #3: 0.6250000
Case #4: 0.3164062
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
