We have N cards numbered 1, 2, ..., N. Card i (1 \leq i \leq N) has an integer A_i written in red ink on one side and an integer B_i written in blue ink on the other side. Initially, these cards are arranged from left to right in the order from Card 1 to Card N, with the red numbers facing up.

Determine whether it is possible to have a non-decreasing sequence facing up from left to right (that is, for each i (1 \leq i \leq N - 1), the integer facing up on the (i+1)-th card from the left is not less than the integer facing up on the i-th card from the left) by repeating the operation below. If the answer is yes, find the minimum number of operations required to achieve it.

* Choose an integer i (1 \leq i \leq N - 1). Swap the i-th and (i+1)-th cards from the left, then flip these two cards.

Constraints

* 1 \leq N \leq 18
* 1 \leq A_i, B_i \leq 50 (1 \leq i \leq N)
* All values in
input are integers.

Input

Input is given from Standard Input in the following format:


N
A_1 A_2 ... A_N
B_1 B_2 ... B_N


Output

If it is impossible to have a non-decreasing sequence, print `-1`. If it is possible, print the minimum number of operations required to achieve it.

Examples

Input

3
3 4 3
3 2 3


Output

1


Input

2
2 1
1 2


Output

-1


Input

4
1 2 3 4
5 6 7 8


Output

0


Input

5
28 15 22 43 31
20 22 43 33 32


Output

-1


Input

5
4 46 6 38 43
33 15 18 27 37


Output

3

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
