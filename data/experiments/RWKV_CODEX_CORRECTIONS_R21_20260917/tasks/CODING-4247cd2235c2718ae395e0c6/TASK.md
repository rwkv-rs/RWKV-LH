With the advent of high-speed graphic workstations, CAD (Computer-Aided Design), and other fields (CAM, VLSI design), the use of computers has become increasingly efficient. One question related to rendering images is the elimination of hidden lines (lines obscured by other parts of the drawing).

You need to design a program to help architects draw the skyline of a given city location.

To simplify the problem, all buildings are rectangular. They share a common base (the city they are built on is very flat). The city is also considered two-dimensional.

A building is specified by an ordered triplet $(L_i,H_i,R_i)$. $L_i$ and $R_i$ are the positions of the left and right sides of building $i$, and $H_i$ is the height of building $i$.

The illustration of buildings below is represented by a sequence of triplets.

```
(1, 11, 5), (2, 6, 7), (3, 13, 9), (12, 7, 16), (14, 3, 25), (19, 18, 22), (23, 13, 29), (24, 4, 28)
```

The skyline shown on the right is represented by the sequence:
(1, 11, 3, 13, 9, 0, 12, 7, 16, 3, 19, 18, 22, 3, 23, 13, 29, 0)

Input

The input is a sequence of triplets constructing the buildings. All coordinates for the buildings are integers less than $10000$.

There is at least one and at most $5000$ buildings in the input file. Each building is given on a separate line.

All integers in the triplet are separated by one or more spaces. The triplets are sorted by $L_i$.

The leftmost X-coordinate in the system is the smallest building, so the X-coordinate is the first in the input file.

Output

The output should consist of the vector describing the Skyline as defined above.

In the Skyline vector $(v_1,v_2,v_3,\cdots,v_{n-2},v_{n-1},v_n)$, when $i$ is even, it represents a horizontal line (height). When $i$ is odd, it represents a vertical line (X-coordinate).

The Skyline vector should represent a "path" starting with the smallest value to ensure continuity.

X-coordinates can move in both the horizontal and vertical of all defined Skyline lines. Therefore, the last entry in all Skyline vectors is $0$.

Translated by @Wuge

## Sample Input and Output

### Sample Input #1

```
1 11 5
2 6 7
3 13 9
12 7 16
14 3 25
19 18 22
23 13 29
24 4 28
```

### Sample Output #1

```
1 11 3 13 9 0 12 7 16 3 19 18 22 3 23 13 29 0
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
