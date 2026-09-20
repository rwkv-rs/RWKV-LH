The rabbit has prepared a Christmas tree for Christmas.

As astute participants may have noticed, the Christmas tree is, of course, a tree structure in graph theory. The tree consists of $ N $ vertices (vertices $ 1, 2, ..., N $) and has $ N-1 $ edges. The $ i $th ($ 1 \leq i \leq N-1 $) edge connects vertex $ A_i $ and vertex $ B_i $ with a length of $ C_i $.

The rabbit has $ K $ bulbs and is trying to decorate the tree by placing each bulb on a vertex. However, the bulbs the rabbit has are very high-powered, so placing too many bulbs close to each other would make the tree too dazzling. Therefore, the rabbit decided to place the bulbs as far apart as possible. Here, the distance between the bulbs is the distance between the vertices where the bulbs are installed. The distance between two vertices is the minimum sum of the lengths of the edges traversed to go from one vertex to the other.

When placing $ K $ bulbs on $ N $ vertices to light them up, consider the minimum distance $ d $ between the bulbs. Find the maximum value that $ d $ can take.

## Input Format

The input is given from the standard input in the following format:

> $ N $ $ K $ $ A_1 $ $ B_1 $ $ C_1 $ $ A_2 $ $ B_2 $ $ C_2 $ $ : $ $ A_{N-1} $ $ B_{N-1} $ $ C_{N-1} $

## Output Format

Output the maximum value that the minimum distance $ d $ between the bulbs can take in one line.

## Sample Input and Output

### Sample Input #1

```
4 3
2 1 100
3 2 200
4 2 300
```

### Sample Output #1

```
300
```

### Sample Input #2

```
9 4
1 2 1
1 3 1
3 4 1
1 5 1
6 5 1
7 5 1
8 5 1
9 8 1
```

### Sample Output #2

```
3
```

### Sample Input #3

```
6 2
1 2 20
1 3 16
1 4 1224
4 5 1400
4 6 1700
```

### Sample Output #3

```
3100
```

### Sample Input #4

```
12 4
4 8 1214
12 7 890
3 1 651
5 9 1990
1 2 1671
4 1 55
6 4 761
7 2 862
11 10 1469
11 7 1122
12 9 364
```

### Sample Output #4

```
2940
```

## Notes/Hints

### Constraints

- $ 2 \leq K \leq N \leq 200,000 $.
- $ 1 \leq A_i, B_i \leq N $.
- $ 1 \leq C_i \leq 5,000 $.
- $ A_i \neq B_i $.
- The input is guaranteed to represent a tree structure.

### Partial Points

- If you correctly solve the dataset where $ N \leq 40,000 $, you will be awarded $ 50 $ points.
- If you correctly solve the dataset without additional constraints, you will be awarded an additional $ 50 $ points.

### Sample Explanation 1

Decorating vertices $ 1, 3, 4 $ is good.

### Sample Explanation 2

Decorating vertices $ 2, 4, 6, 9 $ is good.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
