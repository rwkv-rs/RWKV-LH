Alice and Bob are playing a game again.

They have a sequence consisting of $n$ positive integers, each of which is $\le n$. The elements in the sequence are numbered from $1$ to $n$. The sequence may contain duplicate numbers. At the start of the game, a multiset $S$ is initialized with the first $p$ elements of the sequence. Alice goes first. In each turn of the game:

1. The player selects a number from $S$ and removes it from $S$, then adds the value of this number to their score (both players start with a score of zero).
2. The next number in the sequence (if any remain) is added to the set $S$ (if the sequence is empty, this step is skipped). That is, after removing the first number, the $(p+1)$-th number in the sequence is added to the set, after the second number, the $(p+2)$-th number is added, and so on.

The game continues until $S$ is empty. Both players are assumed to be very smart (i.e., they always maximize their own benefit). The result of the game is Alice's score minus Bob's score.

Your task is to write a program that calculates the results of $k$ games (with the same sequence).

## Input Format

The first line contains two positive integers $n$ and $k$.

The second line contains $n$ positive integers $a_1, a_2, ..., a_n$, describing the initial sequence.

The third line contains $k$ positive integers $p_1, p_2, ..., p_k$, where $p_i$ indicates that for the $i$-th game, $p = p_i$.

## Output Format

The output should contain $k$ positive integers, one per line.

The $i$-th positive integer represents the result of the $i$-th game.

## Sample Input and Output

### Sample Input #1

```
5 2
2 4 2 3 5
4 3
```

### Sample Output #1

```
2
6
```

## Notes/Hints

### Sample 1 Explanation

The input specifies that you need to handle $2$ games. Both games use the same sequence but start with different multisets $S$. The first game starts with $\{2, 4, 2, 3\}$, and the second game starts with $\{2, 4, 2\}$.

### Data Size and Constraints

- For the first $10\%$ of the data, $1 \le n \le 10$.
- For the first $30\%$ of the data, $1 \le n \le 600$.
- For the first $50\%$ of the data, $1 \le n \le 10^4, 1 \le k \le 10^3$.
- For all data, $1 \le n \le 10^5, 1 \le k \le 2 \times 10^3, k \le n, a_i \in [1, n], p_i \in [1, n]$.

### Original Problem Source

Original problem from: [eJOI2017](http://ejoi.org) Problem F. [Game](http://ejoi.org/wp-content/themes/ejoi/assets/pdfs/tasks_day_2/EN/game_statement-en.pdf)

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
