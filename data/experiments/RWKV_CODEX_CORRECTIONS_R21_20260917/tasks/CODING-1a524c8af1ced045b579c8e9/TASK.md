### Problem Description

There is a deck of cards with two suits: red and black. Each suit has $M$ cards. These cards are arranged in a certain order, and the top $8$ cards are used to build a house-like structure, as shown in the illustration.

![](https://cdn.luogu.com.cn/upload/image_hosting/jsc1kxvi.png)

The remaining cards are laid out openly on the table so that both players know them.

Axel and Birgit are playing a game. Axel plays with the red cards, and Birgit with the black. The player with the card on the leftmost position goes first. As shown, the first card is $6B$, so Birgit goes first.

Players take turns performing one of the following actions with the leftmost card:

- Hold the card in hand (only if there is no card already in hand).

- Place a card between two adjacent peaks to form a roof (using the card in hand or the newly picked one), forming a level surface. Any leftover card (if any) is held in hand.

- Form a peak by placing the card in hand atop the newly picked one, on an existing roof.

**Note: Only one card can be held in hand.**

Each time a triangle is formed (upward or downward), the player with the majority color in the triangle earns points equal to the sum of the card values.

When all cards from the table are picked, if a player still holds a card, they perform the following: if the card's color matches their own, they gain points; otherwise, they lose points. The points equal the card's value.

Both players are highly skilled and aim to calculate how much more one player can score over the other.

### Input Format

**Multiple Test Cases**

For each test case:
The first line contains the name of the player whose score is to be maximized.

The second line contains an integer $M$.

The third line lists the $2M$ cards in the order given, with each combination of suit and value appearing only once.

The end of input is marked by the string END.

### Output Format

For each test case, print the maximum score difference in the following format:

If the specified player is Axel: "Case X: Axel wins D"  
If the specified player is Birgit: "Case X: Birgit loses D"  
If they tie: "Case X: Axel and Birgit tie"

### Sample Input
```
Axel

5

1R 2R 3R 4R 5R 5B 4B 3B 2B 1B

Birgit

5

1R 2R 3R 4R 5R 5B 4B 3B 2B 1B

Birgit

5

1R 1B 3R 4R 5R 5B 4B 3B 2R 2B

End
```

### Sample Output
```
Case 1: Axel wins 1

Case 2: Birgit loses 1

Case 3: Axel and Birgit tie
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
