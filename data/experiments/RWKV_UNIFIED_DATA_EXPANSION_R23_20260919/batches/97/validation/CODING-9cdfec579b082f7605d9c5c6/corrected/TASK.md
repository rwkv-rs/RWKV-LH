One day, Hongcow goes to the store and sees a brand new deck of n special cards. Each individual card is either red or blue. He decides he wants to buy them immediately. To do this, he needs to play a game with the owner of the store.

This game takes some number of turns to complete. On a turn, Hongcow may do one of two things: 

  * Collect tokens. Hongcow collects 1 red token and 1 blue token by choosing this option (thus, 2 tokens in total per one operation). 
  * Buy a card. Hongcow chooses some card and spends tokens to purchase it as specified below. 



The i-th card requires ri red resources and bi blue resources. Suppose Hongcow currently has A red cards and B blue cards. Then, the i-th card will require Hongcow to spend max(ri - A, 0) red tokens, and max(bi - B, 0) blue tokens. Note, only tokens disappear, but the cards stay with Hongcow forever. Each card can be bought only once.

Given a description of the cards and their costs determine the minimum number of turns Hongcow needs to purchase all cards.
Input

The first line of input will contain a single integer n (1 ≤ n ≤ 16).

The next n lines of input will contain three tokens ci, ri and bi. ci will be 'R' or 'B', denoting the color of the card as red or blue. ri will be an integer denoting the amount of red resources required to obtain the card, and bi will be an integer denoting the amount of blue resources required to obtain the card (0 ≤ ri, bi ≤ 107).

Output

Output a single integer, denoting the minimum number of turns needed to acquire all the cards.

Examples

Input

3
R 0 1
B 1 0
R 1 1


Output

4


Input

3
R 3 0
R 2 0
R 1 0


Output

6

Note

For the first sample, Hongcow's four moves are as follows: 

  1. Collect tokens 
  2. Buy card 1
  3. Buy card 2
  4. Buy card 3

Note, at the fourth step, Hongcow is able to buy card 3 because Hongcow already has one red and one blue card, so we don't need to collect tokens.

For the second sample, one optimal strategy is as follows: 

  1. Collect tokens 
  2. Collect tokens 
  3. Buy card 2
  4. Collect tokens 
  5. Buy card 3
  6. Buy card 1

At the fifth step, even though Hongcow has a red token, Hongcow doesn't actually need to spend it, since Hongcow has a red card already.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
