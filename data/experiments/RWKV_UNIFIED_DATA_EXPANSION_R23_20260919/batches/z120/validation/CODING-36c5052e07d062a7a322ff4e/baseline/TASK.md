You must remember the story of the foolish Fusu and the mischievous Xiao F playing cards. This time, they are playing a very new type of card game.

## Problem Description

Initially, both Fusu and Xiao F have $n$ cards each. Each card has a suit $f$ and a point value $p$. In this problem, the suit is a positive integer not exceeding $m$, and the point value is a positive integer not exceeding $r$.

We define a 'round of play' as starting from one person, both players take turns following the rules to play their cards until one player cannot play a card that meets the requirements.

In a round of play, the first player to play will play the card with the **smallest point value**. If there are multiple cards with the smallest point value, the card with the **smallest point value and smallest suit** is played. Then, both players take turns playing cards, the rule being to play the card with the **same suit as the opponent's last played card and a point value greater than the opponent's last played card's point value, with the smallest such point value**. If such a card does not exist, the round ends, and the next round starts with the **opponent** (i.e., the player who played the last card in this round starts the next round).

Given the cards of both players and the player who starts the first round, please determine who finishes their cards first.

## Input Format

**This problem contains multiple test cases within a single test point.**

The first line of input is an integer representing the number of test cases $T$. The following lines contain the input information for each case:

The first line contains four integers: the number of cards $n$, the upper bound of suits $m$, the upper bound of point values $r$, and the player who starts the first round $s$. $s = 1$ means Fusu starts, and $s = 2$ means Xiao F starts.  
The second line contains $n$ integers, the $i$-th integer represents the suit $f1_i$ of Fusu's $i$-th card.  
The third line contains $n$ integers, the $i$-th integer represents the point value $p1_i$ of Fusu's $i$-th card.  
The fourth line contains $n$ integers, the $i$-th integer represents the suit $f2_i$ of Xiao F's $i$-th card.  
The fifth line contains $n$ integers, the $i$-th integer represents the point value $p2_i$ of Xiao F's $i$-th card.

## Output Format

For each case, output a string on a single line. If Fusu finishes their cards first, output `FS wins!`; if Xiao F finishes their cards first, output `FR wins!`.

## Sample Input and Output

### Sample Input #1

```
1
3 1 2 1
1 1 1
1 2 1
1 1 1
2 2 1
```

### Sample Output #1

```
FS wins!
```

### Sample Input #2

```
1
3 1 2 2
1 1 1
1 2 1
1 1 1
2 2 1
```

### Sample Output #2

```
FR wins!
```

## Notes

## Data Range and Constraints

- For $10\%$ of the data, $r = 1$;
- For $20\%$ of the data, $n = 1$;
- For $50\%$ of the data, $m = 1$;
- For $100\%$ of the data, $1 \leq T \leq 10$, $1 \leq n, m, r \leq 100$, $1 \leq s \leq 2$, $1 \leq f1_i, f2_i \leq m$, $1 \leq p1_i, p2_i \leq r$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
