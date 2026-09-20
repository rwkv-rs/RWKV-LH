Xiaotu enjoys running at the playground in the evening. Today, after running two laps, he started playing a game.

The playground is a convex polygon with \( n \) vertices, numbered counterclockwise from \( 0 \) to \( n - 1 \). Xiaotu randomly stands at some position on the playground, marked as point \( p \). Connecting point \( p \) with each of the \( n \) vertices forms \( n \) triangles. If the area of the triangle formed by points \( p \), \( 0 \), and \( 1 \) is the smallest among the \( n \) triangles, Xiaotu considers this a correct stance.

Now, Xiaotu wants to know the probability of a correct stance.

## Input Format

The first line contains one integer \( n \), representing the number of vertices of the playground and the number of games.

The next \( n \) lines each contain two integers \( x_i \) and \( y_i \), representing the coordinates of the vertices.

The input guarantees that the points are provided in counterclockwise order and that they form a convex polygon. It also guarantees that no three points are collinear.

## Output Format

Output one number, the probability of a correct stance, rounded to four decimal places.

## Sample Input and Output

### Input Sample #1

```
5
1 8
0 7
0 0
8 0
8 8
```

### Output Sample #1

```
0.6316
```

## Notes/Hints

For 30% of the data, \( 3 \leq n \leq 4 \), \( 0 \leq x, y \leq 10 \)

For 100% of the data, \( 3 \leq n \leq 10^5 \), \( -10^9 \leq x, y \leq 10^9 \)

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
