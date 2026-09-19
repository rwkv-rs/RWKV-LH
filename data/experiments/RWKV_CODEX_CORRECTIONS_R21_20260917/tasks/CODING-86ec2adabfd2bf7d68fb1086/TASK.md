This is a village filled with love, named Double Town. In this village brimming with affection, the residents live happily and peacefully. Double Town is shaped like a long strip, consisting of $N$ squares arranged in a row. Each square can be either empty or contain one of the following items: grass, shrubs, trees, houses, or castles. Each item has a level, with grass being level $1$, shrubs level $2$, and so on.

You are the builder of this village. You will receive $D$ items sequentially, and you need to place them reasonably on the empty squares of the village. Your goal is to maximize the village's total popularity, which is explained later. The rules for placement are as follows:

* First, each item must be placed somewhere; it cannot be discarded. If there are no empty squares left, the game ends immediately.
* Second, items can be placed on an empty square or temporarily stored in a warehouse. The warehouse can hold at most one item at a time and starts empty. There is only one warehouse.
* Third, once an item is placed on a square, if conditions are met, the system will automatically combine some items into a larger item. This is mandatory and instantaneous. Only after the combination is complete can the next item be placed.
* Fourth, items stored in the warehouse can be taken out and placed on an empty square at any time (but not during the combination process), or they can remain in the warehouse.
* Fifth, unless using the warehouse, the order of item placement cannot be changed.

In summary, the game's flow is to receive a new item, decide whether to store it in the warehouse, then decide whether to place the item from the warehouse or the new item on an empty square, the system automatically determines the combination, gains popularity, and continues until all items are placed or there are no empty squares left.

The rules for combination are as follows. Combination is automatic and mandatory. If there are two or more adjacent squares with items of the same level, they will automatically combine into a new item, with the new item's level being one higher. The combination process consists of three steps:

* First, determine how many items participate in the combination; these items must be contiguous and of the same level. The participating items will disappear, and the corresponding squares will become empty.
* Second, if $A$ items of level $K$ participate in the combination, then $A \times 2^K$ popularity points will be gained. For example, if five pieces of grass combine, the total popularity will increase by $5 \times 2^1 = 10$.
* Third, a level $K+1$ item will appear in one of the squares. If $K+1$ is greater than $5$, this step is skipped, but the popularity from the second step is still counted, and the old items from the first step are cleared. The higher-level item will only appear in the squares that participated in the combination. Each square records the last time it was placed with an item. The new item will appear in the square that was most recently placed with an item.

Finally, note that combinations can trigger multiple times, such as two pieces of grass combining into a shrub, and if there are other shrubs nearby, the combination will continue.

Given $N$ and the sequence and levels of the items received, you need to place these items in a village that starts with all empty squares to maximize the village's final popularity. When all items are placed or there are no empty squares left, you will end the village's construction, and the accumulated popularity at that time will be your final achievement.

## Input Format

The first line contains two integers $N$ and $D$, separated by a space. $N$ represents the size of the village, and $D$ represents the number of days for village construction.

The second line is a string, where each character is a digit from $1$ to $5$, indicating the level of the item you can place each day.

## Output Format

Output a single integer, representing the maximum popularity value you can achieve.

## Sample Input and Output

### Sample Input #1

```
4 10
1132411235
```

### Sample Output #1

```
168
```

## Notes/Hints

For $30\%$ of the data, $N=3$, $D\leq 10$.

For $60\%$ of the data, $N\leq 4$, $D\leq 30$.

For $100\%$ of the data, $N\leq 6$, $D\leq 100$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
