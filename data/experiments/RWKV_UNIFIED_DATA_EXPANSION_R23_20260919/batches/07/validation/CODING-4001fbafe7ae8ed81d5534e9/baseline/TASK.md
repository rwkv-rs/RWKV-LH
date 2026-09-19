There are N integers written on a blackboard. The i-th integer is A_i, and the greatest common divisor of these integers is 1.

Takahashi and Aoki will play a game using these integers. In this game, starting from Takahashi the two player alternately perform the following operation:

* Select one integer on the blackboard that is not less than 2, and subtract 1 from the integer.
* Then, divide all the integers on the black board by g, where g is the greatest common divisor of the integers written on the blackboard.



The player who is left with only 1s on the blackboard and thus cannot perform the operation, loses the game. Assuming that both players play optimally, determine the winner of the game.

Constraints

* 1 ≦ N ≦ 10^5
* 1 ≦ A_i ≦ 10^9
* The greatest common divisor of the integers from A_1 through A_N is 1.
Input

The input is given from Standard Input in the following format:


N
A_1 A_2 … A_N


Output

If Takahashi will win, print `First`. If Aoki will win, print `Second`.

Examples

Input

3
3 6 7


Output

First


Input

4
1 2 4 8


Output

First


Input

5
7 8 8 8 8


Output

Second

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
