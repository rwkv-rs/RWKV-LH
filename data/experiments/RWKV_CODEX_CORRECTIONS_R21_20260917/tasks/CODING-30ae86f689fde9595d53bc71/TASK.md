oolimry has an array $$$a$$$ of length $$$n$$$ which he really likes. Today, you have changed his array to $$$b$$$, a permutation of $$$a$$$, to make him sad.

Because oolimry is only a duck, he can only perform the following operation to restore his array:

- Choose two integers $$$i,j$$$ such that $$$1 \leq i,j \leq n$$$.
- Swap $$$b_i$$$ and $$$b_j$$$.

The sadness of the array $$$b$$$ is the minimum number of operations needed to transform $$$b$$$ into $$$a$$$.

Given the arrays $$$a$$$ and $$$b$$$, where $$$b$$$ is a permutation of $$$a$$$, determine if $$$b$$$ has the maximum sadness over all permutations of $$$a$$$.

Input

Each test contains multiple test cases. The first line contains a single integer $$$t$$$ ($$$1 \leq t \leq 10^4$$$)  — the number of test cases. The description of the test cases follows.

The first line of each test case contains a single integer $$$n$$$ ($$$1 \leq n \leq 2 \cdot 10^5$$$)  — the length of the array.

The second line of each test case contains $$$n$$$ integers $$$a_1, a_2, \ldots, a_n$$$ ($$$1 \leq a_i \leq n$$$)  — the elements of the array $$$a$$$.

The third line of each test case contains $$$n$$$ integers $$$b_1, b_2, \ldots, b_n$$$ ($$$1 \leq b_i \leq n$$$)  — the elements of the array $$$b$$$.

It is guaranteed that $$$b$$$ is a permutation of $$$a$$$.

It is guaranteed that the sum of $$$n$$$ over all test cases does not exceed $$$2 \cdot 10^5$$$.

Output

For each test case, print "AC" (without quotes) if $$$b$$$ has the maximum sadness over all permutations of $$$a$$$, and "WA" (without quotes) otherwise.

Examples

Input

4
2
2 1
1 2
4
1 2 3 3
3 3 2 1
2
2 1
2 1
4
1 2 3 3
3 2 3 1

Output

AC
AC
WA
WA

Note

In the first test case, the array $$$[1,2]$$$ has sadness $$$1$$$. We can transform $$$[1,2]$$$ into $$$[2,1]$$$ using one operation with $$$(i,j)=(1,2)$$$.

In the second test case, the array $$$[3,3,2,1]$$$ has sadness $$$2$$$. We can transform $$$[3,3,2,1]$$$ into $$$[1,2,3,3]$$$ with two operations with $$$(i,j)=(1,4)$$$ and $$$(i,j)=(2,3)$$$ respectively.

In the third test case, the array $$$[2,1]$$$ has sadness $$$0$$$.

In the fourth test case, the array $$$[3,2,3,1]$$$ has sadness $$$1$$$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
