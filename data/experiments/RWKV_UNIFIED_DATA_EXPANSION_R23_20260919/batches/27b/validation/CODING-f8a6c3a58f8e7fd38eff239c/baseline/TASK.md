### Problem Statement:

Determine the minimum number of folds required to transform a rectangle of dimensions $W \times H$ into a rectangle of dimensions $w \times h$, where each fold must be parallel to one of the sides of the rectangle.

------------

### Input Format:

The first line contains two positive integers $W$ and $H$. The second line contains two positive integers $w$ and $h$.

$1 \le W, H, w, h \le 10^9$

------------

### Output Format:

Output the minimum number of folds required. If it is not possible to transform the rectangle through folding, output `-1`.

## Problem Description

As you may recall, Alex is passionate about origami. She has moved from working with squares to rectangles, which are significantly more challenging. Her primary interest is to determine the minimum number of folds needed to transform a $W \times H$ rectangle into a $w \times h$ rectangle. Each fold must result in a rectangular shape, so only folds parallel to the sides of the rectangle are allowed.

Help Alex by writing a program that calculates the minimum number of folds required.

## Input Format

The first line of the input contains two integers $W$ and $H$ — the initial dimensions of the rectangle. The second line contains two integers $w$ and $h$ — the target dimensions of the rectangle $(1 \le W, H, w, h \le 10^9)$.

## Output Format

Output a single integer — the minimum number of folds needed to transform the initial rectangle into the target rectangle. If the transformation is not possible, output `-1`.

## Sample Input and Output

### Sample Input #1

```
2 7
2 2
```

### Sample Output #1

```
2
```

### Sample Input #2

```
10 6
4 8
```

### Sample Output #2

```
2
```

### Sample Input #3

```
5 5
1 6
```

### Sample Output #3

```
-1
```

## Notes

Time limit: 2 seconds, Memory limit: 256 MB.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
