You are given the positions of some rectangles and circles on a plane, as well as the coordinates of certain points.

Determine in which figure (if any) each point is contained.

## Input Format

Initially, each line will contain a lowercase letter `c` or `r`.

If it's `r`, it represents a rectangle, defined by four values:

The coordinates of the top-left corner $(x_1, y_1)$ and the bottom-right corner $(x_2, y_2)$.

If it's `c`, it represents a circle, defined by three values:

The coordinates of the center $(x, y)$ and the radius.

Input for figures stops when a line with `*` is encountered.

Afterwards, each line contains two numbers, representing the coordinates of a point $(x, y)$.

When the coordinates are $(9999.9, 9999.9)$, input for points stops.

## Output Format

For each point, output which figure it is contained in, if any.

For example, if point 1 is contained in figure 3, output `Point 1 is contained in figure 3`.

If point 2 is not contained in any figure, output `Point 2 is not contained in any figure`.

## Input Example #1

```
r 8.5 17.0 25.5 -8.5
c 20.2 7.3 5.8
r 0.0 10.3 5.5 0.0
c -5.0 -5.0 3.7
r 2.5 12.5 12.5 2.5
c 5.0 15.0 7.2
*
2.0 2.0
4.7 5.3
6.9 11.2
20.0 20.0
17.6 3.2
-5.2 -7.8
9999.9 9999.9
```

## Output Example #1

```
Point 1 is contained in figure 3
Point 2 is contained in figure 3
Point 2 is contained in figure 5
Point 3 is contained in figure 5
Point 3 is contained in figure 6
Point 4 is not contained in any figure
Point 5 is contained in figure 1
Point 5 is contained in figure 2
Point 6 is contained in figure 4
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
