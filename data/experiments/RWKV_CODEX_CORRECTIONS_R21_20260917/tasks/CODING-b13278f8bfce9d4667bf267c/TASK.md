Jiangsu Changzhou High School is a prestigious institution with a century-long history, where countless memories linger. Will recalls that before the school underwent renovations, there was a tall metasequoia forest on campus. Every time the metasequoia leaves fell, the needle-like leaves would blanket the ground, creating a romantic and leisurely walk. Back then, Will and his classmates enjoyed playing a game called "Leaf Picking" under the metasequoia trees. At the start of the game, everyone would spread \( n \) leaves flat on the ground. Then, in each round, a student could choose a leaf and move it horizontally or vertically (i.e., to infinity)—as long as the movement was not obstructed by any unmoved leaves. If a leaf's movement was blocked in a round, the move was illegal and not allowed. After \( n \) rounds, when all the leaves were moved, the game ended. However, not all leaves could be moved at any time. When there were many leaves, determining whether a leaf could be moved in a specific direction in each round was a cumbersome task. Now, we abstract the ground into a Cartesian coordinate system, and the \( n \) leaves into \( n \) non-intersecting line segments, numbered from 1 to \( n \). Will also provides the number of the leaf he wants to move and the direction of movement for each round. Please help him:

1. Identify the earliest round where an illegal move occurs.
2. Provide a valid sequence of moves to complete the game.

Note: Touching at endpoints does not count as obstruction, as detailed in the sample cases.

## Input Format

The first line of the input file contains a positive integer \( n \), representing the number of leaves.

The next \( n \) lines, each containing 4 integers, describe the position information of the leaves. The \( i \)-th line contains integers \( a_i \), \( b_i \), \( c_i \), \( d_i \), indicating that the endpoints of the line segment abstracted from the \( i \)-th leaf are \( (a_i, b_i) \) and \( (c_i, d_i) \).

The following \( n \) lines, each containing 2 integers, describe the move operations. The \( i \)-th line contains integers \( p_i \), \( q_i \), indicating that in the \( i \)-th round, the leaf numbered \( p_i \) is moved in the direction \( q_i \). Here, \( q_i \) is an integer between 0 and 3, where 0 means moving left (negative \( x \)-axis direction), 1 means moving up (positive \( y \)-axis direction), 2 means moving right, and 3 means moving down.

The input data guarantees:

- All segments have positive lengths, no two segments share a common point, and no segment is vertical or horizontal.
- \( p_1 \) to \( p_n \) form a permutation of 1 to \( n \).
- There is definitely an illegal move in Will's provided move operations.
- A completely legal sequence of \( n \) moves always exists.

## Output Format

The output file contains \( n + 1 \) lines.

The first line contains an integer between 1 and \( n \), indicating the earliest round where an illegal move occurs.

The next \( n \) lines, each containing two integers as described in the input format, describe a valid sequence of moves.

## Sample Input and Output

### Input Sample #1

```
5 
2 5 5 8 
2 1 3 5 
5 2 6 5 
7 0 4 2 
3 1 4 0 
2 0 
3 0 
4 0 
1 2 
5 1 
```

### Output Sample #1

```
3 
2 0 
3 0 
4 3 
1 2 
5 1 
```

### Input Sample #2

```
4
-1 1 2 3
13 5 9 8
10 10 15 14
10 17 0 20
3 1
2 1
1 1

4 1
```

### Output Sample #2

```
2
4 1
3 1
2 1
1 1
```

## Notes/Hints

In Will's provided move sequence, in the 3rd round, the leaf numbered 4 moving left would be obstructed by the leaf numbered 5.

For detailed data ranges, please refer to the table provided in the problem content.

For a test case:

- If the illegal move is correctly identified but the provided sequence is incorrect, 5 points can be obtained. A message `An invalid move in step` will be shown.
- If the illegal move is incorrectly identified but the provided sequence is correct, 5 points can be obtained. A message `Negative error detection!` will be shown.
- If both the illegal move identification and the sequence are correct, 10 points can be obtained.
- Otherwise, 0 points will be awarded.

If the output format is incorrect, it will be directly judged as such and result in 0 points.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
