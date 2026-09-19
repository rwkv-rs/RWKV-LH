SK drew $n$ rectangles on paper, where the $i$-th rectangle is described by the quintuple $(x_i, y_i, w_i, h_i, \phi_i)$. Specifically, the rectangle has a width (horizontal direction) of $w_i$ and a height (vertical direction) of $h_i$. The coordinates of its **geometric center** are $(x_i, y_i)$, and it is rotated **clockwise** by ${\phi_i}^{\circ}$ around the center.

SK wants you to calculate the percentage of the area occupied by these $n$ rectangles with respect to the area of the convex hull formed by their vertices. Formally, let the sum of the rectangles' areas be $S$, and the area of the convex hull formed by the rectangles' vertices be $S'$. You need to find $\dfrac{S}{S'}\times 100\%$. **This problem has specific output format requirements, so pay close attention.**

You need to solve $T$ sets of test data.

## Input Format

**This problem contains multiple sets of test data.**

The first line of the input file is the integer $T$, representing the number of data sets;

For each set of data, there are $(n+1)$ lines:

- The first line, an integer $n$, represents the number of rectangles;

- The following $n$ lines, each containing five **real numbers** $x_i, y_i, w_i, h_i, \phi_i$, describe a rectangle.

## Output Format

For each data set, output one line. If the percentage you calculate is $p\%$, you should output `p %` **(with a space in between)**, **where $\boldsymbol{p}$ is rounded to one decimal place.**

## Notes

For $100\%$ of the data, ensure that:

- $1\le T\le 50$;
- $1\le n\le 600$;
- $0\le x_i, y_i, w_i, h_i\le 10^4$;
- $\phi_i\in (-90,90]$;
- The given rectangles do not intersect with each other.

Below is an illustrative diagram of the sample input.

![](https://cdn.luogu.com.cn/upload/image_hosting/fs6w5nj3.png)

## Input and Output Example

### Input Example #1

```
1
4
4 7.5 6 3 0
8 11.5 6 3 0
9.5 6 6 3 90
4.5 3 4.4721 2.2361 26.565
```

### Output Example #1

```
64.3 %
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
