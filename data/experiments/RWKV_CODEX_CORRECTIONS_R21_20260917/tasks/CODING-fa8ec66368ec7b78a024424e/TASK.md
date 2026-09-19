Alice, Bob, and Cynthia are always troubled by their chaotic debts. Finally, one day, they decided to sit down together to solve this problem. However, verifying the authenticity of banknotes is a tedious task, so they want to minimize the amount of cash exchanged when settling debts.

For example, Alice owes Bob 10 yuan, and Cynthia is not indebted to either of them. Suppose Alice has only one 50 yuan note, Bob has three 10 yuan notes and ten 1 yuan notes, and Cynthia has three 20 yuan notes. A straightforward approach would be: Alice gives the 50 yuan to Bob, and Bob gives his money back to Alice, resulting in 14 banknotes being exchanged. However, this is not the best approach. The optimal solution is: Alice gives the 50 yuan to Cynthia, Cynthia gives two 20 yuan notes to Alice and one 20 yuan note to Bob, and Bob gives one 10 yuan note to Cynthia, resulting in only 5 banknotes being exchanged.

Soon, they realize this is a tricky problem, so they turn to you, a skilled mathematician, to solve this dilemma.

## Input Format

The first line of input includes three integers: $x_1$, $x_2$, $x_3$ (-1,000 ≤ $x_1$, $x_2$, $x_3$ ≤ 1,000), where

- $x_1$ represents the amount Alice owes Bob (if $x_1$ is negative, it means Bob owes Alice money)
- $x_2$ represents the amount Bob owes Cynthia (if $x_2$ is negative, it means Cynthia owes Bob money)
- $x_3$ represents the amount Cynthia owes Alice (if $x_3$ is negative, it means Alice owes Cynthia money)

The next three lines each include six natural numbers:

- a100, a50, a20, a10, a5, a1
- b100, b50, b20, b10, b5, b1
- c100, c50, c20, c10, c5, c1

a100 indicates the number of 100 yuan notes Alice has, b50 indicates the number of 50 yuan notes Bob has, and so on. Additionally, we guarantee that a10 + a5 + a1 ≤ 30, b10 + b5 + b1 ≤ 30, c10 + c5 + c1 ≤ 30, and the total face value of banknotes held by the three individuals will not exceed 1,000.

## Output Format

If the debts can be settled, output the minimum number of banknotes that need to be exchanged. If it is impossible to settle the debts, output "impossible" (note the word is all lowercase, and do not include quotes when outputting to a file).

## Sample Input and Output

### Sample Input #1

```
10 0 0
0 1 0 0 0 0
0 0 0 3 0 10
0 0 3 0 0 0
```

### Sample Output #1

```
5
```

### Sample Input #2

```
-10 -10 -10
0 0 0 0 0 0
0 0 0 0 0 0
0 0 0 0 0 0
```

### Sample Output #2

```
0
```

## Notes

For 30% of the data, $x_1$, $x_2$, $x_3$ ≤ |50|.
For 100% of the data, $x_1$, $x_2$, $x_3$ ≤ |1,000|.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
