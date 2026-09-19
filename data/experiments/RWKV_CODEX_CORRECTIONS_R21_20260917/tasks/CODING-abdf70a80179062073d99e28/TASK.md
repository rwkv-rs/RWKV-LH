There are $n$ types of numbers, where the $i$-th type is $a_i$ with $b_i$ instances and a weight of $c_i$.

Two numbers $a_i$ and $a_j$ can be paired if $a_i$ is a multiple of $a_j$ and $a_i/a_j$ is a prime number.

Pairing these two numbers yields a value of $c_i \times c_j$.

Each number can participate in at most one pairing and may choose not to participate.

Given that the total value obtained is not less than $0$, determine the maximum number of pairings possible.

## Input Format

The first line contains an integer $n$.

The second line contains $n$ integers $a_1, a_2, \cdots, a_n$.

The third line contains $n$ integers $b_1, b_2, \cdots, b_n$.

The fourth line contains $n$ integers $c_1, c_2, \cdots, c_n$.

## Output Format

Output a single number, the maximum number of pairings.

## Sample Input and Output

### Input Sample #1

```
3
2 4 8
2 200 7
-1 -2 1
```

### Output Sample #1

```
4
```

## Notes/Hints

Test cases $1 \sim 3$: $n \leq 10$, $a_i \leq 10^9$, $b_i = 1$, $|c_i| \leq 10^5$;

Test cases $4 \sim 5$: $n \leq 200$, $a_i \leq 10^9$, $b_i \leq 10^5$, $c_i = 0$;

Test cases $6 \sim 10$: $n \leq 200$, $a_i \leq 10^9$, $b_i \leq 10^5$, $|c_i| \leq 10^5$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
