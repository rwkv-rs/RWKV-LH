A cyclic grid is a matrix where all elements are arrows pointing to one of the four adjacent cells. Each element has coordinates (row, column), with the top-left element at (0,0). Given a starting position (r, c), you can move between cells following the direction of the arrows. For example, if (r, c) is a left arrow, you move to (r, c-1); if it's a right arrow, you move to (r, c+1); if it's an up arrow, you move to (r-1, c); if it's a down arrow, you move to (r+1, c). Both rows and columns are cyclic, meaning if you move out of bounds, you appear on the opposite side. For instance, in a 5x5 cyclic grid, moving left from (3,0) would place you at (3,4).

## Problem Description

A perfect cyclic grid is defined such that for any starting position, you can follow the arrows back to the starting position. If a cyclic grid is not perfect, you can modify any element's arrow to make it perfect. For example, the left grid below is not perfect because only starting from (1,1), (1,2), (2,0), and (2,3) will return you to the start. By modifying two arrows, the right grid becomes a perfect cyclic grid.

![](https://cdn.luogu.com.cn/upload/pic/10987.png)

Given a cyclic grid, you need to calculate the minimum number of elements to modify to make it perfect.

## Input Format

The first line contains two integers R and C, representing the rows and columns of the cyclic grid. The next R lines each contain C characters (LRUD) indicating left, right, up, and down directions.

## Output Format

An integer representing the minimum number of elements to modify to make the given cyclic grid perfect.

## Sample Input and Output

### Input Sample #1

```
4 4
RRRD
URDD
UULD
ULLL
```

### Output Sample #1

```
0
```

### Input Sample #2

```
3 4
RRRD
URLL
LRRR
```

### Output Sample #2

```
2
```

## Notes

### Data Range

30% of the data: 1 ≤ R, C ≤ 7

100% of the data: 1 ≤ R, C ≤ 15

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
