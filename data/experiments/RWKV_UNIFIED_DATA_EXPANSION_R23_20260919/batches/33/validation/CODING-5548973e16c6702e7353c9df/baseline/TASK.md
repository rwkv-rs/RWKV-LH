Two players, A and B, are playing a stone-picking game. They have a pile of $n$ stones, and A starts first. The rules are as follows: A can pick no more than $k$ stones on the first turn, and each subsequent player can pick no more than twice the number of stones the previous player picked. Each player must pick at least one stone. The player who picks the last stone loses, and the other player wins. Given $k$, you need to determine how many integers $n$ between 1 and $N$ (inclusive) allow A to have a guaranteed winning strategy.

## Input Format

**Multiple test cases.**

The first line contains a positive integer $T$ representing the number of test cases.

The next $T$ lines each contain two integers $k$ and $N$ separated by a space, representing a query.

## Output Format

Output $T$ lines, each containing an integer representing the answer in the order of input.

## Sample Input and Output

### Sample Input #1

```
3
1 5
2 5
1 10
```

### Sample Output #1

```
2
3
4
```

## Notes

### Sample Explanation

For the first sample, when $k=1$:

- If $n=1$, A can only take the only stone and loses.
- If $n=2$, A takes one stone, and B can only take the last stone, so A wins.
- If $n=3$, A takes one stone, B takes one stone, and A is forced to take the last stone and loses.
- If $n=4$, A takes one stone, B takes two stones, and A is forced to take the last stone and loses.
- If $n=5$, A takes one stone, B can take one or two stones, and A can always leave the last stone for B, so A wins.

### Data Range and Hints

For all data, $1 \le T \le 10^5, k, N \le 10^{18}$.

- For 10% of the data, $T, N \le 500$.
- For another 20% of the data, $T, N \le 10^5$.
- For another 20% of the data, $T \le 3, N \le 3 \times 10^6$.
- For another 20% of the data, $k=1$.
- For the remaining 30% of the data, there are no special restrictions.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
