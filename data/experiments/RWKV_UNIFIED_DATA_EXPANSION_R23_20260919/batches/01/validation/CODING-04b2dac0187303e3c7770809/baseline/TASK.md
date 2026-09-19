Roy and October are playing a game of stone picking.

## Problem Description

The rules of the game are as follows: There are $n$ stones, and each player can only take $p^k$ stones at a time (where $p$ is a prime number, $k$ is a natural number, and $p^k$ is less than or equal to the remaining number of stones). The player who takes the last stone wins.

October goes first. The question is whether she has a guaranteed winning strategy.

If she does, output one line `October wins!`; otherwise, output one line `Roy wins!`.

## Input Format

The first line contains a positive integer $T$, representing the number of test cases.

From the second line to the $T+1$-th line, each line contains a positive integer $n$, representing the number of stones.

## Output Format

$T$ lines, each line either `October wins!` or `Roy wins!`.

## Sample Input and Output

### Input Sample #1

```
3
4
9
14
```

### Output Sample #1

```
October wins!
October wins!
October wins!
```

## Notes

For $30\%$ of the data, $1 \leq n \leq 30$;

For $60\%$ of the data, $1 \leq n \leq 10^6$;

For $100\%$ of the data, $1 \leq n \leq 5 \times 10^7$, $1 \leq T \leq 10^5$.

(Adapted problem)

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
