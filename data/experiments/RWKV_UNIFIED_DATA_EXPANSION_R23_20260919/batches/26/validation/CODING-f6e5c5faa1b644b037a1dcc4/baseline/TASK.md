There are currently $n$ coins, each with potentially different values. The value of the $i$-th coin is $v_i$.

The task is to divide these coins into two groups such that the difference in the number of coins between the two groups does not exceed 1. The goal is to minimize the difference in the total value of the two groups.

## Input Format

**This problem contains multiple test cases within a single test point.**

The first line of input is a positive integer $T$, indicating the number of test cases within the test point.

Each test case consists of two lines:

- The first line contains an integer $n$, representing the number of coins.
- The second line contains $n$ integers, where the $i$-th integer represents the value $v_i$ of the $i$-th coin.

## Output Format

For each test case, output a single integer on a new line, representing the minimum possible difference in the total value of the two groups of coins.

## Sample Input and Output

### Input Sample #1

```
2
3
2 2 4
4
1 2 3 6
```

### Output Sample #1

```
0
2
```

## Notes

### Data Size and Constraints

- For 30% of the data, it is guaranteed that $1 \leq v_i \leq 1000$.
- For 100% of the data, it is guaranteed that $1 \leq T \leq 20$, $1 \leq n \leq 30$, and $1 \leq v_i \leq 2^{30}$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
