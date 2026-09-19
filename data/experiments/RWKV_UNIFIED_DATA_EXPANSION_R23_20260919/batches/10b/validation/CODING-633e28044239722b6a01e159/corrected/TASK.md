**[Problem Description]**

Given a point $M$ and a polyline graph formed by $n$ connected segments (composed of $n+1$ points), find the coordinates of the point $P$ on this polyline that is closest to point $M$ (point $P$ can be on any segment).

**[Input]**

The input consists of multiple datasets, and the input ends at EOF.

For each dataset, the first two lines contain the coordinates of point $M$. The next line contains an integer $n$, followed by $2(n+1)$ lines representing the coordinates of the $n+1$ points forming the polyline.

**[Output]**

For each dataset, output two lines representing the x and y coordinates of point $P$.

**[Example Explanation]**

For the first dataset, the coordinates of $M$ are $(6,-3)$, $n$ is $3$, and the coordinates of the polyline's points are $(0,1),(5,5),(9,-5),(15,3)$.

## Input and Output Example

### Sample Input #1

```
6
-3
3
0
1
5
5
9
-5
15
3
0
0
1
1
0
2
0
```

### Sample Output #1

```
7.8966
-2.2414
1.0000
0.0000
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
