The Painter's Studio is preparing mass production of paintings. Paintings are going to be made with aid of square matrices of various sizes. A matrix of size _i_ consists of 2 _$ ^{i} $_  rows and 2 _$ ^{i} $_  columns. There are holes on intersections of some rows and columns. Matrix of size 0 has one hole. For _i_ > 0, matrix of size _i_ is built of four squares of size 2 $ ^{(} $  _$ ^{i} $_  $ ^{-1)} $ \*2 $ ^{(} $  _$ ^{i} $_  $ ^{-1)} $ . Look at the following figure:

![](https://cdn.luogu.com.cn/upload/vjudge_pic/SP174/104973dafa2ff5ffca869a0fb29e8194ed4634f6.png)

Both squares on the right side and the bottom-left square are matrices of size _i_-1. Top-left square has no holes. Pictures are constructed in the following way. First, we fix three non-negative integers _n_, _x_, _y_. Next, we take two matrices of size _n_, place one of them onto the other and shift the upper one _x_ columns right and _y_ rows up. We place such a pattern on a white canvas and cover the common part of matrices with the yellow paint. In this way we get yellow stains on the canvas in the places where the holes in both matrices agree.

## Input Format

The number of test cases _t_ is in the first line of input, then _t_ test cases follow separated by an empty line

There is one integer _n_, 0 <= _n_ <= 100 in the first line of each test case. This number is the size of matrices used for production of paintings. In the second line there is one integer _x_ and in the third line one integer _y_, where 0 <= _x_,_y_ <= 2 _$ ^{n} $_ . The integer _x_ is the number of columns and _y_ is the number of rows that the upper matrix should be shifted by.

## Output Format

For each test case your program should produce one line with exactly one integer - the number of stains on the canvas.

## Sample Input and Output

### Sample Input #1

```
The number of test cases t is in the first line of input, then t test cases follow separated by an empty line
There is one integer n, 0 &lt;= n &lt;= 100 in the first line of each test case. This number is the size of matrices used for production of paintings. In the second line there is one integer x and in the third line one integer y, where 0 &lt;= x,y &lt;= 2n. The integer x is the number of columns and y is the number of rows that the upper matrix should be shifted by.
```

### Sample Output #1

```
For each test case your program should produce one line with exactly one integer - the number of stains on the canvas.

Example
Sample input:
1
2
2
2

Sample output:
3
```

### Sample Input #2

```
1
2
2
2
```

### Sample Output #2

```
None
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
