**Problem Description:**

You are given two points, A and B, located on the surface of a parallelepiped. Your task is to calculate the square of the shortest path length from point A to point B. The dimensions of the rectangular box, \( l, w, h \), and the coordinates of the points are all integers.

**Input Format:**

The input consists of multiple lines. Each line contains \( l, w, h (1 \le l, w, h \le 1000) \) and \( x_a, y_a, z_a, x_b, y_b, z_b (0 \le x_a, x_b \le l, 0 \le y_a, y_b \le w, 0 \le z_a, z_b \le h) \). Here, \( x_a, y_a, z_a \) represent the coordinates of point A, and \( x_b, y_b, z_b \) represent the coordinates of point B.

**Output Format:**

Output a single integer per line, representing the square of the shortest path length on the surface from point A to point B.

## Input and Output Examples

### Example Input #1

```
5 5 2 3 1 2 3 5 0
300 600 900 300 550 0 0 550 900
```

### Example Output #1

```
36
970000
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
