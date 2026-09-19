There is a sequence of length $N$, where the $i$-th element is $a_i$.

There are $Q$ modifications, where the $j$-th modification changes the $i_j$-th element to $x_j$.

You need to find the maximum sum of the largest and second-largest values among any consecutive $K$ elements in the sequence, both initially and after each modification.

## Input Format

The first line contains three integers $N, K, Q$ as described in the problem.
The second line contains $N$ integers $a_i$ representing the sequence.
The next $Q$ lines each contain two integers $i_j, x_j$ representing a modification.

## Output Format

Output $Q+1$ lines, where the $j$-th line represents the answer after the $j-1$-th modification, with the first line representing the answer before any modifications.

## Sample Input and Output

### Input Sample #1

```
4 3 1
6 1 2 4
1 3
```

### Output Sample #1

```
8
6
```

## Notes/Hints

### Sample Explanation

For Sample #1:

- Before any modifications, selecting the range $[1, 3]$ yields a sum of $6 + 2 = 8$.
- After the first modification, selecting the range $[2, 4]$ yields a sum of $2 + 4 = 6$.

### Data Constraints

For $100\%$ of the data, $2 \le N \le 10^6$, $2 \le K \le N$, $0 \le Q \le 10^5$, $0 \le a_i \le 10^9$, $1 \le i_j \le N$, $0 \le x_j \le 10^9$.
For $20\%$ of the data, $Q = 0$.
For another $40\%$ of the data, $N \le 10^4$.

### Note

Translated from the [Canadian Computing Olympiad 2018](https://cemc.math.uwaterloo.ca/contests/computing/2018/) Day 2 [B Boring Lectures](https://cemc.math.uwaterloo.ca/contests/computing/2018/stage%202/day2.pdf).

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
