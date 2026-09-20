Ever since getting hooked on jigsaw puzzles, JYY has become a complete otaku. To solve his food and shelter issues, JYY has to rely on ordering takeout to sustain his life.

## Problem Description

There are a total of $n$ types of food at the takeout restaurant, numbered from $1$ to $n$. Each type of food has a fixed price $p_i$ and a shelf life $s_i$. The $i$-th type of food will expire $s_i$ days after purchase. JYY does not eat expired food.

For example, if JYY orders food with a shelf life of 1 day, he must consume it either today or tomorrow; otherwise, it will no longer be edible. The shelf life can be 0 days, meaning the food must be eaten on the day of purchase.

JYY currently has $m$ dollars. Each time he orders takeout, he needs to pay an additional delivery fee of $f$ dollars to the delivery guy.

The delivery guy is strong and can instantly bring JYY any number of food items. JYY wants to know, under the condition that he can eat at least one unexpired takeout meal every day, how many days he can stay indoors at most?

## Input Format

The first line contains three integers, representing $m$, $f$, and $n$ respectively.

From the second line to the $(n + 1)$-th line, each line contains two integers, where the $(i + 1)$-th line represents the price $p_i$ and shelf life $s_i$ of the $i$-th type of food.

## Output Format

Output a single integer, representing the maximum number of days JYY can stay indoors.

## Sample Input and Output

### Sample Input #1

```
32 5 2
5 0
10 2
```

### Sample Output #1

```
3
```

## Notes

### Sample Input and Output 1 Explanation

JYY's optimal strategy is:
- On the first day, buy one food item $1$ and one food item $2$ and eat one food item $1$;
- On the second day, eat one food item $2$;
- On the third day, buy one food item $1$ and eat it.

### Data Range and Constraints

For all test cases, it is guaranteed that $1 \leq n \leq 200$, $0 \leq s_i \leq 10^{18}$, $1 \leq f, p_i, m \leq 10^{18}$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
