Little A discovered a tree laden with fruits in an orchard and decided to take a portion of it home.

## Problem Description

The tree can be represented as a tree structure, meaning there is exactly one path between any two nodes. At each node \( i \), there is a fruit with a value \( v_i \) and a weight \( w_i \). Little A wants to take a part (or all) of the tree, including at least \( K \) nodes (i.e., at least \( K \) fruits), with the highest possible average value. The average value is defined as the total value of the fruits divided by the total weight. Note that the portion of the tree Little A cuts must be a connected part of the original tree.

## Input Format

The first line contains two numbers \( N \) and \( K \), representing the number of nodes in the tree and the minimum number of fruits Little A should take, respectively.

The second line contains \( N \) space-separated numbers, representing the value \( v_i \) of the fruit at each node.

The third line contains \( N \) space-separated numbers, representing the weight \( w_i \) of each fruit.

The next \( N-1 \) lines each contain two numbers \( a_i \) and \( b_i \) (\( 1 \le a_i, b_i \le N \)), indicating an edge between nodes \( a_i \) and \( b_i \). The input guarantees a correct tree structure.

## Output Format

Output a single line containing a number, representing the maximum possible average value, rounded to two decimal places.

## Sample Input and Output

### Input Sample #1

```
3 1
20 10 20
1 1 1
1 2
2 3
```

### Output Sample #1

```
20.00
```

### Input Sample #2

```
3 2
20 10 20
1 1 1
1 2
2 3
```

### Output Sample #2

```
16.67
```

## Notes

### Data Size and Constraints

- For \( 20\% \) of the data, \( 1 \le N \le 16 \);
- For \( 100\% \) of the data, \( 1 \le N \le 100 \), \( 1 \le K \le N \), \( 1 \le v_i \le 10000 \), \( 1 \le w_i \le 10000 \).

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
