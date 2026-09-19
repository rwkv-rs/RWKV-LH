lsq invites wzt to his house to play poker.

## Problem Description

lsq's poker deck does not include jokers, totaling n cards. Since wzt is obsessed with exponentiation, he proposes to draw a^2 cards each time (where "^" denotes exponentiation). lsq finds this boring and changes it to drawing a^k cards each time (k is a natural number chosen freely by the player). **Starting with lsq**, players take turns drawing cards according to this rule, and the one who draws the last card wins.

Given ample time, lsq and wzt will play q games, each with different values of a and n. wzt has coded a solution that can determine the winning strategy once a and n are fixed. Impressed by your skills, lsq wants you to write a program to determine if he can win given a and n, without needing to calculate the optimal moves.

**Note: Both players will always use a winning strategy if available.**

Here, k is a non-negative integer that can be chosen by the player each time they draw cards. Refer to the sample cases for better understanding.

## Input Format

The first line contains a number q, indicating the number of games.
The next q lines each contain two integers a and n, as described above.

## Output Format

Output q lines.
If lsq can win, output "lsq Win".
If wzt can win, output "wzt Win".

## Sample Input and Output

### Sample Input #1

```
3
2 5
2 9
3 9
```

### Sample Output #1

```
lsq Win
wzt Win
lsq Win
```

## Notes

For 30% of the data, q ≤ 30, a ≤ 30, n ≤ 1e8.
For 50% of the data, q ≤ 50, a ≤ 30, n ≤ 1e12.
For 100% of the data, q ≤ 50000, a ≤ 20000, n ≤ 1e500.

Sample Explanation:
Query 1: lsq is guaranteed to win. He can start by drawing 2^1 = 2 cards, and regardless of whether wzt draws 2^1 = 2 or 2^0 = 1, lsq can finish drawing the cards. Other strategies follow similarly (just different orders).

Query 2: wzt is guaranteed to win. If lsq starts by drawing 2^0 = 1, wzt can draw 2^3 = 8; if lsq starts by drawing 2^1 = 2, wzt can draw 2^2 = 4. Regardless of whether lsq draws 2^1 = 2 or 2^0 = 1 next, wzt can finish drawing the cards. Other strategies follow similarly (just different orders).

Query 3: lsq is guaranteed to win. He can simply draw 3^2 = 9 cards.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
