Given a sequence of $N$ integers $A_1, A_2, \dots, A_N$. Let $M = \max\{A_1, A_2, \dots, A_N\}$.

You need to find the largest integer $K$ such that the first $K$ numbers from left to right are all less than the next $K$ numbers.

## Input Format

The first line contains two integers $M$ and $N$, representing the maximum number in the sequence and the number of integers, respectively.

The second line contains $N$ integers $A_1, A_2, \dots, A_N$.

## Output Format

Output a single integer, which is the largest $K$.

## Sample Input and Output

### Sample Input #1

```
5 10
2 2 1 4 3 2 5 4 2 3
```

### Sample Output #1

```
4
```

## Notes

For $100\%$ of the data, it is guaranteed that $1 \le M \le 2 \times 10^3$, $1 \le N \le 2 \times 10^4$, and $1 \le A_i \le M$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
