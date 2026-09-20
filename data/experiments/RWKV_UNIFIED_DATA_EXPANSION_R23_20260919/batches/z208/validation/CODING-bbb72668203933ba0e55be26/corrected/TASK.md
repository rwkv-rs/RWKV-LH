Xiao X is piloting his spaceship to traverse a $n$-dimensional space, where each point can be represented by $n$ real numbers, namely $(x_1, x_2, \ldots, x_n)$.

To pass through this space, Xiao X needs to select $c$ ($c \geq 2$) points in this space as the stops for his spaceship. These points must satisfy the following three conditions:

1. Each coordinate of every point is a positive integer, and the $i$-th coordinate does not exceed $m_i$.
2. The $j$-th coordinate of the $(i+1)$-th point ($1 \leq i < c$) must be strictly greater than the $j$-th coordinate of the $i$-th point ($1 \leq j \leq n$).
3. There exists a straight line passing through all the selected points. In this $n$-dimensional space, a straight line can be represented by $2n$ real numbers $p_1, p_2, \ldots, p_n, v_1, v_2, \ldots, v_n$. The line passes through the point $(x_1, x_2, \ldots, x_n)$ if and only if there exists a real number $t$ such that for $i = 1, \ldots, n$, $x_i = p_i + tv_i$.

Xiao X has not yet determined his final plan. Please help him calculate how many different plans satisfy his requirements. Since the answer may be very large, you only need to output the value of the answer modulo $10,007$.

## Input Format

The first line of the input file `space.in` contains a positive integer $T$, indicating the number of test cases to be solved.

Each test case contains two lines. The first line contains two positive integers $n$ and $c$ ($c \geq 2$), representing the dimensions of the space and the number of points to be selected, respectively.

The second line contains $n$ positive integers, representing $m_1, m_2, \ldots, m_n$ in order.

## Output Format

The output file `space.out` contains $T$ lines, each containing a non-negative integer, corresponding to the answer for each test case in order.

## Sample Input and Output

### Sample Input #1

```
3
2 3
3 4
3 3
3 4 4
4 4
5 9 7 8
```

### Sample Output #1

```
2
4
846
```

### Sample Input #2

```
1
11 20
97665 99289 91440 92389 93960 94623 96582 93975 98359 93492 90331
```

### Sample Output #2

```
3278
```

## Notes

**Sample 1 Explanation**

For the first set of sample data, there are two feasible plans: one is to select $(1,1)$, $(2,2)$, $(3,3)$, and the other is to select $(1,2)$, $(2,3)$, $(3,4)$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
