Given an integer $n$ and a list of $m$ prime numbers $p$.

You can perform any number of operations. In each operation, you choose a prime number $p_i$, which changes $n$ to $\lfloor \frac{n}{p_i}\rfloor \times p_i$.

Your goal is to determine the minimum number of operations required to reduce $n$ to $0$. If it is impossible to reduce $n$ to $0$, output `oo`.

To increase the difficulty, you need to answer $Q$ queries of $n$.

## Input Format

The first line contains two integers $m$ and $Q$.

The next line contains $m$ integers $p$.

The following $Q$ lines each contain an integer $n$, representing the $n$ for each query.

## Output Format

For each query, output the minimum number of operations required to reduce $n$ to $0$, or `oo` if it is impossible.

## Sample Input and Output

### Input Sample #1

```
2 2
2 3
5
6
```

### Output Sample #1

```
3
oo
```

## Notes

### Data Range and Constraints
- For 20% of the data, $m, n, Q \leq 10^4$.
- For another 20% of the data, $Q = 1$.
- For 100% of the data, $1 \leq m, Q \leq 10^5$, $2 \leq p_i \leq 10^7$ and $p_i$ is a prime number, $1 \leq n \leq 10^7$.

### Notes
This problem is translated from the [Baltic Olympiad in Informatics 2013](https://boi.cses.fi/tasks.php) [Day 2](https://boi.cses.fi/files/boi2013_day2.pdf) T1 Brunhilda’s Birthday.

Due to the lack of a suitable setting, the full score for this problem is 110 points.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
