You are given an integer \( n \) followed by \( n \) points \((x_i, y_i)\). These \( n \) points form a polygon in sequence. (It is guaranteed that each edge of the polygon is either parallel or perpendicular to the coordinate axes, the points are distinct, no points lie on the edges, and the edges do not intersect each other.)

Determine the length of the edges that are considered safe.

(An edge of unit length is safe if and only if it can meet with other edges when shifted outward. Refer to the diagram for clarification.)

## Input Format

The first line contains an integer \( n \), representing the number of vertices.

The next \( n \) lines each contain two integers \( x_i \) and \( y_i \), representing the coordinates of each vertex.

## Output Format

Output a single integer, representing the total length of the safe edges.

## Problem Description

In Perpendicularia, there are only two directions: vertical and horizontal. The Perpendicularia government plans to build a new secret service facility. They have several proposed facility plans and want to calculate the total secured perimeter for each of them.

The total secured perimeter is calculated as the total length of the facility walls that are invisible to an observer looking perpendicularly from outside. The figure below shows one of the proposed plans and the corresponding secured perimeter.

![](https://onlinejudgeimages.s3-ap-northeast-1.amazonaws.com/problem/15139/1.png)

Write a program that calculates the total secured perimeter for the given plan of the secret service facility.

## Input Format

The plan of the secret service facility is specified as a polygon.

The first line of the input contains one integer \( n \) -- the number of vertices of the polygon \((4 \le n \le 1000)\). Each of the following \( n \) lines contains two integers \( x_i \) and \( y_i \) -- the coordinates of the \( i \)-th vertex \((-10^6 \le x_i, y_i \le 10^6)\). Vertices are listed in consecutive order.

All polygon vertices are distinct, and none of them lie on the polygon's edges. All polygon edges are either vertical \((x_i = x_{i+1})\) or horizontal \((y_i = y_{i+1})\), and none of them intersect each other.

## Output Format

Output a single integer -- the total secured perimeter of the secret service facility.

## Sample Input and Output

### Sample Input #1

```
10
1 1
6 1
6 4
3 4
3 3
5 3
5 2
2 2
2 3
1 3
```

### Sample Output #1

```
6
```

## Notes/Hints

Time limit: 3 seconds, Memory limit: 512 MB.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
