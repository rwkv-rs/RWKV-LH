Given a convex polygon with \( n \) vertices in order, where each vertex \( (x_i, y_i) \) has integer coordinates \( x_i, y_i \in [-10^9, 10^9] \).

Determine the number of diagonals that can divide the polygon into two parts, each with an integer area.

## Problem Description

Ingrid runs a polygon shop in a distant country, specializing in selling convex polygons with integer coordinates. Her customers prefer polygons that can be divided into two halves by a straight diagonal, starting and ending at vertices of the polygon, such that both halves have non-empty, integer areas. The more ways a polygon can be divided in this manner, the more valuable it is.

For instance, the left polygon in the image below can be divided in three proper ways, while the right one can be divided in two ways.

![Image](https://cdn.luogu.com.cn/upload/image_hosting/fei0xc33.png)

As the business grows, Ingrid needs an automated tool to determine the number of proper ways to divide a polygon. This is crucial for her shop, as manually setting prices for a large number of polygons would be extremely time-consuming. Can you help Ingrid by writing this tool?

## Input Format

The first line of the input contains an integer \( n \) — the number of polygon vertices \( (4 \le n \le 200,000) \). Each of the following \( n \) lines contains the coordinates of a vertex: a pair of integers \( x_i \) and \( y_i \) per line \( (-10^9 \le x_i, y_i \le 10^9) \). The polygon is convex, and its vertices are specified in the order of traversal.

## Output Format

Output a single integer \( w \) — the number of ways to divide the polygon in the proper way.

## Sample Input and Output

### Sample Input #1

```
5
7 3
3 5
1 4
2 1
5 0
```

### Sample Output #1

```
3
```

### Sample Input #2

```
4
1 1
3 1
5 5
1 3
```

### Sample Output #2

```
2
```

## Notes/Hints

Time limit: 2 seconds, Memory limit: 256 MB.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
