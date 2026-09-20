Alice, Bob and Charlie are playing Card Game for Three, as below:

* At first, each of the three players has a deck consisting of some number of cards. Alice's deck has N cards, Bob's deck has M cards, and Charlie's deck has K cards. Each card has a letter `a`, `b` or `c` written on it. The orders of the cards in the decks cannot be rearranged.
* The players take turns. Alice goes first.
* If the current player's deck contains at least one card, discard the top card in the deck. Then, the player whose name begins with the letter on the discarded card, takes the next turn. (For example, if the card says `a`, Alice takes the next turn.)
* If the current player's deck is empty, the game ends and the current player wins the game.



There are 3^{N+M+K} possible patters of the three player's initial decks. Among these patterns, how many will lead to Alice's victory?

Since the answer can be large, print the count modulo 1\,000\,000\,007 (=10^9+7).

Constraints

* 1 \leq N \leq 3×10^5
* 1 \leq M \leq 3×10^5
* 1 \leq K \leq 3×10^5
Input

The input is given from Standard Input in the following format:


N M K


Output

Print the answer modulo 1\,000\,000\,007 (=10^9+7).

Examples

Input

1 1 1


Output

17


Input

4 2 2


Output

1227


Input

1000 1000 1000


Output

261790852

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
