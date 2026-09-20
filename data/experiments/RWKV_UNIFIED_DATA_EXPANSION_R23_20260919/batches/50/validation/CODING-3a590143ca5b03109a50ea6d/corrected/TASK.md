Alice and Bob are playing a game with n coins numbered from 1 to n. Each coin has two sides, which we refer to as heads and tails. Initially, some coins are heads up and others are tails up. Alice and Bob will take turns flipping these coins, with Alice always going first.

Specifically, each player can choose a coin numbered x that is currently tails up. For the number x, we can express it as $c \cdot 2^a \cdot 3^b$, where a and b are non-negative integers, and c is a non-negative integer coprime with 2 and 3. There are two options for flipping:

1. Choose integers p and q such that $a \ge pq$, $p \ge 1$, and $1 \leq q \leq \text{MAXQ}$. Then flip all coins numbered $c \cdot 2^{a-pj} \cdot 3^b$ for $j = 0, 1, 2, \ldots, q$.

2. Choose integers p and q such that $b \ge pq$, $p \ge 1$, and $1 \leq q \leq \text{MAXQ}$. Then flip all coins numbered $c \cdot 2^a \cdot 3^{b-pj}$ for $j = 0, 1, 2, \ldots, q$.

The game cannot continue indefinitely, and the player who cannot make a valid move loses. As the first player, Alice wants to know if she can guarantee a win before the game starts. She knows that both she and Bob are very smart and will optimize their strategies to ensure they do not lose.

## Input Format

The input contains multiple test cases. The first line contains an integer T, representing the total number of test cases. Each test case is described as follows:

- The first line of each test case contains two integers n and MAXQ.
- The second line contains n integers, where the i-th integer indicates the initial state of the i-th coin (0 for tails up, 1 for heads up).

## Output Format

The output consists of T lines. For each test case, if Alice can guarantee a win, output "win" (without quotes). Otherwise, output "lose".

## Sample Input and Output

### Input Sample #1

```
6
16 14
1 0 0 1 0 0 0 0 1 0 0 0 1 0 1 1
16 14
0 1 0 0 0 1 1 1 1 1 1 0 1 0 0 1
16 11
0 1 0 0 0 1 1 1 0 1 0 0 0 1 0 1
16 12
1 1 1 1 1 1 1 1 0 0 1 1 0 1 1 0
16 4
1 0 0 1 0 0 1 0 0 0 0 1 0 1 1 0
16 20
0 0 0 0 1 0 1 0 0 0 1 0 0 1 0 0
```

### Output Sample #1

```
win
lose
win
lose
win
win
```

## Notes

For 100% of the data, $1 \le n \le 30000$, $1 \le MAXQ \le 20$, and $t \le 100$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
