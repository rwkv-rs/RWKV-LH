Little A and Little B are lost in a two-dimensional space. Each of them follows a specific path, which is periodic. You can understand these paths as "tracks": closed paths where the end coincides with the start, allowing for periodic movement.

## Problem Description

Both individuals move at a speed of one unit distance per second, and their paths are parallel to the coordinate axes. Given this, if they continue to move indefinitely, we want to know the closest distance between them at each second. (We only consider the distance between them after each second of movement, not at any moment within that second.)

## Input and Output Formats

### Input Format

The input file contains two similar sections, each describing the movement track of Little A and Little B. In each section, the first line contains three integers: sx, sy, and m. The first two integers represent the initial position, and the third integer represents the number of line segments in the track. The following m lines each contain an integer d and a non-space character c, separated by a space. d represents the distance Little A or Little B moves along the positive direction of the coordinate, and c is either 'X' or 'Y', indicating the X or Y coordinate axis. The input data guarantees that starting from (sx, sy), after executing m movement steps, we will definitely return to the starting point, meaning the track is closed.

### Output Format

The output file contains only one real number, accurate to two decimal places. It represents the closest observed distance between the two individuals. If it is possible for them to reach the same point at some time, output 0.00.

## Sample Input and Output

### Sample Input #1

```
0 0 4
-1 Y
-1 X
1 Y
1 X
1 0 4
-1 X
1 Y
1 X
-1 Y
```

### Sample Output #1

```
1.00
```

## Notes

For 100% of the data, for any m and d, we have 1 ≤ m, d ≤ 100, and the absolute value of the initial coordinates does not exceed 2,000.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
