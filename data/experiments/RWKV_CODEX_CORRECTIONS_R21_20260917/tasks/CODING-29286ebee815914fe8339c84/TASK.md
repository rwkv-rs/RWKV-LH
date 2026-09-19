WJJ enjoys playing "Warcraft". In the game, the Lich is a powerful hero whose skill Frozen Nova can kill a Wisp each time. We consider both the Lich and the Wisp as points on a plane.

When the straight-line distance between the Lich and the Wisp is no more than R, and the line of sight from the Lich to the Wisp is not blocked by trees (i.e., the line connecting the Lich and the Wisp does not intersect with any tree), the Lich can instantly kill a Wisp.

In the forest, there are N Liches, each needing to wait for a period of time after casting Frozen Nova before they can cast it again. Different Liches have different waiting times and casting ranges, but the same is that each cast can kill a Wisp.

Now, the leader of the Liches wants to know, starting from time 0, the minimum time required to kill all the Wisp.

## Input Format

The first line of the input file contains three integers N, M, K (N, M, K <= 200), representing the number of Liches, the number of Wisp, and the number of trees, respectively.

The next N lines each contain four integers x, y, r, t, representing the coordinates, attack range, and casting interval (in seconds) of each Lich.

The following M lines each contain two integers x, y, representing the coordinates of each Wisp.

The next K lines each contain three integers x, y, r, representing the coordinates of each tree.

All coordinates in the input data have absolute values not exceeding 10000, and the radius and casting interval do not exceed 20000.

## Output Format

Output a single line, the shortest time (in seconds) to kill all the Wisp. If it is impossible to kill all the Wisp, output -1.

## Sample Input and Output

### Input Sample #1

```
2 3 1
-100 0 100 3
100 0 100 5
-100 -10
100 10
110 11
5 5 10
```

### Output Sample #1

```
5
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
