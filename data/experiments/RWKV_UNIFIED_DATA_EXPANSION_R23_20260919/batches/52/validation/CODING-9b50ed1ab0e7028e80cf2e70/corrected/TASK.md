Mahjong is a traditional Chinese entertainment tool. The tiles in Mahjong can be categorized into honor tiles (consisting of East, South, West, North, Red, Green, and White) and numeric tiles (divided into Bamboo, Circles, and Characters, each with nine types from one to nine), with four copies of each type.

In Mahjong, typically, a completed hand consists of fourteen tiles. Among these, two tiles form a pair (identical tiles), and the remaining twelve tiles form four sets of three, each set being either a sequence (numeric tiles of the same suit with consecutive numbers, e.g., Bamboo three, four, five) or a triplet (identical tiles). A ready hand refers to a set of thirteen tiles, which can form a completed hand by adding one specific tile. That added tile is called the waiting tile.

Here, we consider a special variant of Mahjong. In this variant, there are no honor tiles, and only one suit is available. However, the numbers are not limited to one through nine but range from 1 to n. Additionally, there is no restriction of four tiles per type. A completed hand consists of 3m + 2 tiles, with two forming a pair and the remaining 3m tiles forming m sets of three, each set being either a sequence or a triplet. Given a set of 3m + 1 tiles, determine if it is a ready hand and, if so, output all possible waiting tiles.

## Input Format

The input contains two lines. The first line contains two integers n and m (9 ≤ n ≤ 400, 4 ≤ m ≤ 1000) separated by a space. The second line contains 3m + 1 integers separated by spaces, each within the range of 1 to n. These integers represent the numbers of the tiles to be judged for a ready hand.

## Output Format

The output is a single line. If the set of tiles is a ready hand, output all possible waiting tile numbers, separated by a space, in ascending order. If the set of tiles is not a ready hand, output "NO".

## Sample Input and Output

### Sample Input #1

```
9 4
1 1 2 2 3 3 5 5 5 7 8 8 8
```

### Sample Output #1

```
6 7 9
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
