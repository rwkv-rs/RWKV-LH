Gennady and Artem are discussing solutions of different problems.
Gennady told Artem about a number theory problem he solved the day before.
One of steps to solve the problem was to calculate the least common multiple (LCM) of all integers from 1 to n, inclusive.
That problem inspired Gennady to come up with another problem about LCM's.

Given n, find the greatest m that m ≤ n and:
$LCM(1, 2, \ldots, n) = LCM(m, m + 1, \ldots, n)$

We have no doubt Artem will solve the problem, but will you?

You can find the definition of LCM here.
Input format
The only line of the input contains one integer n.

Output format
Print the greatest integer m satisfying the given conditions.

Constraints

1 ≤ n ≤ 10^{15}

SAMPLE INPUT
5

SAMPLE OUTPUT
3

Explanation

LCM(1, 2, 3, 4, 5) = 60
LCM(2, 3, 4, 5) = 60
LCM(3, 4, 5) = 60
LCM(4, 5) = 20

m = 3 is the greatest integer for which LCM(m, m+1, \ldots, 5) = LCM(1, 2, 3, 4, 5) = 60.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
