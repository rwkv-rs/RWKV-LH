There are N cards. The i-th card has an integer A_i written on it. For any two cards, the integers on those cards are different.

Using these cards, Takahashi and Aoki will play the following game:

* Aoki chooses an integer x.
* Starting from Takahashi, the two players alternately take a card. The card should be chosen in the following manner:
* Takahashi should take the card with the largest integer among the remaining card.
* Aoki should take the card with the integer closest to x among the remaining card. If there are multiple such cards, he should take the card with the smallest integer among those cards.
* The game ends when there is no card remaining.



You are given Q candidates for the value of x: X_1, X_2, ..., X_Q. For each i (1 \leq i \leq Q), find the sum of the integers written on the cards that Takahashi will take if Aoki chooses x = X_i.

Constraints

* 2 \leq N \leq 100 000
* 1 \leq Q \leq 100 000
* 1 \leq A_1 < A_2 < ... < A_N \leq 10^9
* 1 \leq X_i \leq 10^9 (1 \leq i \leq Q)
* All values in
input are integers.

Input

Input is given from Standard Input in the following format:


N Q
A_1 A_2 ... A_N
X_1
X_2
:
X_Q


Output

Print Q lines. The i-th line (1 \leq i \leq Q) should contain the answer for x = X_i.

Examples

Input

5 5
3 5 7 11 13
1
4
9
10
13


Output

31
31
27
23
23


Input

4 3
10 20 30 40
2
34
34


Output

70
60
60

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
