For given integers $$$n$$$ and $$$m$$$, let's call a pair of arrays $$$a$$$ and $$$b$$$ of integers good, if they satisfy the following conditions:

- $$$a$$$ and $$$b$$$ have the same length, let their length be $$$k$$$.
- $$$k \ge 2$$$ and $$$a_1 = 0, a_k = n, b_1 = 0, b_k = m$$$.
- For each $$$1 < i \le k$$$ the following holds: $$$a_i \geq a_{i - 1}$$$, $$$b_i \geq b_{i - 1}$$$, and $$$a_i + b_i \neq a_{i - 1} + b_{i - 1}$$$.

Find the sum of $$$|a|$$$ over all good pairs of arrays $$$(a,b)$$$. Since the answer can be very large, output it modulo $$$10^9 + 7$$$.

Input

The input consists of multiple test cases. The first line contains a single integer $$$t (1 \leq t \leq 10^4)$$$  — the number of test cases. The description of the test cases follows.

The only line of each test case contains two integers $$$n$$$ and $$$m$$$ $$$(1 \leq n, m \leq 5 \cdot 10^6)$$$.

It is guaranteed that the sum of $$$n$$$ over all test cases does not exceed $$$5 \cdot 10^6$$$ and the sum of $$$m$$$ over all test cases does not exceed $$$5 \cdot 10^6$$$.

Output

For each test case, output a single integer  — the sum of $$$|a|$$$ over all good pairs of arrays $$$(a,b)$$$ modulo $$$10^9 + 7$$$.

Examples

Input

4
1 1
1 2
2 2
100 100

Output

8
26
101
886336572

Note

In the first testcase, the good pairs of arrays are

- $$$([0, 1], [0, 1])$$$, length = $$$2$$$.
- $$$([0, 1, 1], [0, 0, 1])$$$, length = $$$3$$$.
- $$$([0, 0, 1], [0, 1, 1])$$$, length = $$$3$$$.

Hence the sum of the lengths would be $$${2 + 3 + 3} = 8$$$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
