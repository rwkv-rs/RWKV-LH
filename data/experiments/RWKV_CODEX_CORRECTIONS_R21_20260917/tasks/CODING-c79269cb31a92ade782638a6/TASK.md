You have an $N \times N$ chessboard, where each cell contains an integer, initially all set to $0$. You need to maintain two types of operations:

- `1 x y A`    $1 \le x, y \le N$, $A$ is a positive integer. Add $A$ to the number in cell `x`, `y`.
- `2 x1 y1 x2 y2`    $1 \le x_1 \le x_2 \le N$, $1 \le y_1 \le y_2 \le N$. Output the sum of the numbers within the rectangle defined by $x_1, y_1, x_2, y_2$.
- `3`    Terminate the program.

## Input Format

The first line of the input file contains a positive integer $N$.

Each subsequent line contains an operation. For each command, except the first number, all other numbers are XORed with the last output answer `last_ans`, which is initially $0$.

## Output Format

For each `2` operation, output the corresponding answer.

## Sample Input and Output

### Input Sample #1

```
4
1 2 3 3
2 1 1 3 3
1 1 1 1
2 1 1 0 7
3
```

### Output Sample #1

```
3
5
```

## Notes

$1 \leq N \leq 5 \times 10^5$, the number of operations does not exceed $2 \times 10^5$, memory limit is $20\text{MB}$, and the answers are guaranteed to be within the int range and the decoded data remains valid.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
