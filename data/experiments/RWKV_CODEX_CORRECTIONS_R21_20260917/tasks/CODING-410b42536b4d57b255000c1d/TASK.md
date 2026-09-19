There is a rectangular cake made of blueberries, strawberries, and chocolate. It resembles a square with the bottom-left corner at coordinates $(-5000, -5000)$ and the top-right corner at $(5000, 5000)$. (The unit of the coordinate system is millimeters) The area of the cake is 100 square meters.

Professionals strongly recommend eating this cake with a wet knife and a dry spoon. Additionally:

- Each cut starts from the edge of the cake;
- A single cut cannot entirely lie on the edge of the cake;
- No two cuts have the same starting and ending points; that is, all cutting lines are distinct.

Separation and counting can only be done after the final cut. This means the cake remains rectangular throughout the cutting process.

Your task is to determine: What is the minimum number of cuts required to divide the cake into at least $k$ pieces? Also, output the coordinates of the starting and ending points of each cut.

## Input Format

The input consists of a single line containing an integer $k$, representing the minimum number of pieces the cake should be cut into.

## Output Format

The first line of the output should be an integer $n$, indicating the minimum number of cuts.

The following $n$ lines should each contain four integers, representing the coordinates of the starting and ending points of each cut.

For each point on the edge of the cake, ensure $\max(|x|, |y|) = 5000$.

## Sample Input and Output

### Sample Input #1

```
1
```

### Sample Output #1

```
0
```

### Sample Input #2

```
4
```

### Sample Output #2

```
2
-5000 -5000 5000 5000
5000 -5000 -5000 5000
```

### Sample Input #3

```
7
```

### Sample Output #3

```
3
-5000 5000 0 -5000
-2000 -5000 5000 5000
-5000 0 5000 0
```

## Notes

### Data Size and Constraints

For $100\%$ of the data, it is guaranteed that $1 \le k \le 10^6$.

### Note

**This problem is translated from [COCI2011-2012](https://hsin.hr/coci/archive/2011_2012/) [CONTEST #6](https://hsin.hr/coci/archive/2011_2012/contest6_tasks.pdf) T4 REZ**.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
