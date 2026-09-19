Given the coordinates of vertices of $n$ convex polygons in counterclockwise order, find the area of their intersection. For example, when $n=2$, the two convex polygons are as shown in the following figure:

![](https://cdn.luogu.com.cn/upload/image_hosting/7ieux7g3.png)

The area of the intersection is $5.233$.

## Input Format

The first line contains an integer $n$, representing the number of convex polygons. The following sections describe each polygon in order. The first line of the $i$-th polygon contains an integer $m_i$, representing the number of sides of the polygon. The next $m_i$ lines each contain two integers, providing the coordinates of the vertices in counterclockwise order.

## Output Format

The output file contains a single real number, representing the area of the intersection, rounded to three decimal places.

## Sample Input and Output

### Sample Input #1

```
2
6
-2 0
-1 -2
1 -2
2 0
1 2
-1 2
4
0 -3
1 -1
2 2
-1 0
```

### Sample Output #1

```
5.233
```

## Notes

For $100\%$ of the data: $2 \leq n \leq 10$, $3 \leq m_i \leq 50$, and the coordinates are integers within the range $[-1000,1000]$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
