To write his thesis, `Alex` frequently needs to organize large amounts of data. This time, `Alex` faces a severe challenge: he needs to implement a data structure to maintain a set of points.

Currently, there are $N$ points on a two-dimensional plane.

`Alex` needs to implement the following three operations:

1. Add a point to the set.
2. Given a point, query the minimum Manhattan distance from it to all points in the set.
3. Given a point, query the maximum Manhattan distance from it to all points in the set.

The Manhattan distance between two points is defined as the sum of the absolute differences of their x-coordinates and y-coordinates.

Given the difficulty of this problem, `Alex` naturally cannot solve it and has to ask for your help again.

## Input Format

The first line contains an integer $N$, representing the initial number of points in the set.

The next $N$ lines each contain two integers, representing the x and y coordinates of each point.

The $N+2$nd line contains an integer $Q$, representing the number of queries.

The next $Q$ lines each contain three integers, representing the type of query, the x coordinate, and the y coordinate. Type $0$ indicates adding a point, type $1$ indicates querying the minimum Manhattan distance to that point, and type $2$ indicates querying the maximum Manhattan distance.

## Output Format

Output several lines, each representing the answer to a query operation.

## Sample Input and Output

### Input Sample #1

```
3
7 5
6 2
3 1
5
1 6 1
1 5 5
2 7 1
0 3 2
1 1 0
```

### Output Sample #1

```
1
2
4
3
```

## Notes/Hints

For the first $20\%$ of the data: $1 \le N, Q \le 10^3$

For the first $100\%$ of the data: $1 \le N, Q \le 10^5$

The coordinates of the points are non-negative integers not exceeding $10^9$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
