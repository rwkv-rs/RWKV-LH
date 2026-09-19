There is a spherical space generator that can produce a solid sphere in an $n$-dimensional space. Now, you are trapped inside this $n$-dimensional sphere, and you only know the coordinates of $n+1$ points on the surface of the sphere. You need to determine the center coordinates of this $n$-dimensional sphere as quickly as possible to destroy the spherical space generator.

## Input Format

The first line contains an integer $n$ $(1 \leq n \leq 10)$. The next $n+1$ lines each contain $n$ real numbers, representing the $n$-dimensional coordinates of a point on the sphere. Each real number is accurate to six decimal places, and its absolute value does not exceed $20000$.

## Output Format

There is only one line, listing the $n$-dimensional coordinates of the sphere's center ( $n$ real numbers), with each pair of numbers separated by a space. Each real number should be accurate to three decimal places. The data guarantees a solution. Your answer must exactly match the standard output to score points.

## Sample Input and Output

### Input Sample #1

```
2
0.0 0.0
-1.0 1.0
1.0 0.0
```

### Output Sample #1

```
0.500 1.500
```

## Notes/Hints

Hint: Here are two definitions:

1. **Sphere Center**: The point that has equal distance to any point on the sphere's surface.
2. **Distance**: For two points $A$ and $B$ in an $n$-dimensional space with coordinates $(a_1, a_2, \cdots, a_n)$ and $(b_1, b_2, \cdots, b_n)$, respectively, the distance between $A$ and $B$ is defined as: $dist = \sqrt{(a_1-b_1)^2 + (a_2-b_2)^2 + \cdots + (a_n-b_n)^2}$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
