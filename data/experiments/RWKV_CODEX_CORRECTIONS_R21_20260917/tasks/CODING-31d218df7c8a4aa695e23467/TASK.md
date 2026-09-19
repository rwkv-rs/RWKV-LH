We have N cards arranged in a row on a table.
For each i = 1, 2, \ldots, N, the i-th card has an integer A_i written on the front and an integer B_i written on the back.
Initially, every card is placed face up.
Takahashi will choose any number of cards he likes (possibly zero) and flip them.
Then, he will be happy if the following condition is satisfied:

- for every pair of integers (i, j) such that 1 \leq i \lt j \leq N, the integers visible on the i-th and j-th cards are coprime.

Determine whether it is possible for Takahashi to be happy.

Input

Input is given from Standard Input in the following format:
N
A_1 B_1
A_2 B_2
\vdots
A_N B_N

Output

If it is possible for Takahashi to be happy, print Yes; otherwise, print No.

Constraints


- 1 \leq N \leq 3 \times 10^4
- 1 \leq A_i, B_i \leq 2 \times 10^6
- All values in input are integers.

Sample Input 1

3
2 5
10 9
4 8

Sample Output 1

Yes

Initially, we see integers 2, 10, and 4.
If we flip the first and second cards, we will see 5, 9, and 4, which will make Takahashi happy. Thus, we should print Yes.

Sample Input 2

2
10 100
1000 10000

Sample Output 2

No

There is no way to flip cards to make Takahashi happy, so we should print No.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
