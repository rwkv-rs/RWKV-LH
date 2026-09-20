You are given some rectangles and circles on a plane, along with some points' coordinates.

Determine which figure contains each point.

## Input Format

Initially, each line will contain a lowercase letter `c` or `r`.

- If it is `r`, it represents a rectangle, and it provides four values:
  - The coordinates of the top-left corner $(x_1,y_1)$ and the bottom-right corner $(x_2,y_2)$.
  
- If it is `c`, it represents a circle, and it provides three values:
  - The coordinates of the center $(x,y)$ and the radius.

When the first character of a line is `*`, stop inputting figures.

Subsequently, each line contains two numbers representing the coordinates of a point $(x,y)$.

If the coordinates are $(9999.9,9999.9)$, stop inputting points.

## Output Format

Output, line by line, the information about which figure contains each point.

For example, if point 1 is contained in figure 3, output:

`Point 1 is contained in figure 3`

If point 2 is not contained in any figure, output:

`Point 2 is not contained in any figure`

## Input and Output Example

### Input Example #1

```
r 8.5 17.0 25.5 -8.5
r 0.0 10.3 5.5 0.0
r 2.5 12.5 12.5 2.5
*
2.0 2.0
4.7 5.3
6.9 11.2
20.0 20.0
17.6 3.2
-5.2 -7.8
9999.9 9999.9
```

### Output Example #1

```
Point 1 is contained in figure 2
Point 2 is contained in figure 2
Point 2 is contained in figure 3
Point 3 is contained in figure 3
Point 4 is not contained in any figure
Point 5 is contained in figure 1
Point 6 is not contained in any figure
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
