Little A has recently become obsessed with the game "Gold Miner" and plays it during class. To avoid being caught by the teacher, he has to be very careful, which often leads to his defeat.

After losing all his coins, he seeks your help. Each piece of gold can be considered as a point (with no volume). You are given the coordinates of $N$ pieces of gold, the time required to mine them, and their values. Some pieces of gold are on the same line, and in such cases, you must mine them in order. You can instantly rotate the hook to any angle.

Little A starts at coordinates $(0,0)$. Please help Little A calculate the maximum value of gold he can obtain within time $T$.

## Input Format

The first line contains two integers $N$ and $T$, representing the number of pieces of gold and the total time, respectively.

The next $N$ lines each contain four integers $x$, $y$, $t$, and $v$, representing the coordinates of the gold, the time required to mine it, and its value, respectively.

## Output Format

An integer representing the maximum value that can be obtained within time $T$.

## Sample Input and Output

### Sample Input #1

```
3 10
1 1 1 1
2 2 2 2
1 3 15 9
```

### Sample Output #1

```
3
```

### Sample Input #2

```
3 10
1 1 13 1
2 2 2 2
1 3 4 7
```

### Sample Output #2

```
7
```

## Notes

- For $30\%$ of the data, $0 < T \leq 4 \times 10^3$;
- For $100\%$ of the data, $1 \leq N \leq 200$, $0 < T \leq 4 \times 10^4$.

It is guaranteed that $0 \leq |x| \leq 200$, $0 < y \leq 200$, $0 < t \leq 200$, $0 \leq v \leq 200$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
