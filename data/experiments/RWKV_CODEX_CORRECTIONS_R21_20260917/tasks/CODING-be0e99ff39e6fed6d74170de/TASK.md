### Problem Statement
Given a starting point, an ending point, and $m$ line segments on a plane, where each segment is defined by two endpoints,

determine the minimum number of intersections the line connecting the starting and ending points must make with the existing segments, counting multiple crossings of the same segment multiple times.

The data guarantees that any two segments intersect at most at one point. Note that the connecting line cannot pass through the intersection points, and segments may be diagonal.

The absolute value of the coordinates does not exceed $10^5$.

## Problem Description

Moore’s Law states that the number of transistors on a chip will double every two years. Amazingly, this law has held true for over half a century. Whenever current technology no longer allowed more growth, researchers have come up with new manufacturing technologies to pack circuits even denser. In the near future, this might mean that chips are constructed in three dimensions instead of two. But for this problem, two dimensions will be enough.

A common problem in all two-dimensional hardware design (such as chips, graphics cards, motherboards, etc.) is wire placement. When wires need to cross each other, it becomes problematic. Special devices must be used to allow two electrical wires to pass over each other, which increases manufacturing costs.

Our problem is as follows: you are given a hardware design with several wires already in place (all straight line segments). You are also given the start and end points for a new wire connection to be added. You need to determine the minimum number of existing wires that must be crossed to connect the start and end points. This connection does not have to be a straight line. The only requirement is that it cannot cross at a point where two or more wires already meet or intersect.

![Figure 1: First sample input](https://vj.z180.cn/df2653f5a1b23d354dbe2e33d6438ea6?v=1602904232)

Figure 1 shows the first sample input. Eight existing wires form five squares. The start and end points of the new connection are in the leftmost and rightmost squares, respectively. The black dashed line shows that a direct connection would cross four wires, whereas the optimal solution crosses only two wires (the curved blue line).

## Input Format

The input consists of a single test case. The first line contains five integers $m, x_0, y_0, x_1, y_1$, which are the number of pre-existing wires ($m \le 100$) and the start and end points that need to be connected. This is followed by $m$ lines, each containing four integers $x_a, y_a, x_b, y_b$ describing an existing wire of non-zero length from $(x_a, y_a)$ to $(x_b, y_b)$. The absolute value of each input coordinate is less than $10^5$. Each pair of wires has at most one point in common, that is, wires do not overlap. The start and end points for the new wire do not lie on a pre-existing wire.

## Output Format

Display the minimum number of wires that have to be crossed to connect the start and end points.

## Sample Input and Output

### Sample Input #1

```
8 3 3 19 3
0 1 22 1
0 5 22 5
1 0 1 6
5 0 5 6
9 0 9 6
13 0 13 6
17 0 17 6
21 0 21 6
```

### Sample Output #1

```
2
```

### Sample Input #2

```
1 0 5 10 5
0 0 10 10
```

### Sample Output #2

```
0
```

## Notes

Time limit: 2000 ms, Memory limit: 1048576 kB.

International Collegiate Programming Contest (ACM-ICPC) World Finals 2014

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
