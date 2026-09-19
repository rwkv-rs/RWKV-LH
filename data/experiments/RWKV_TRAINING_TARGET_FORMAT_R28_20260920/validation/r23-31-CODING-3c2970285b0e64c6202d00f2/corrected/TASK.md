In geometry, any square has a unique center point. On a grid-lined plane, this is only true when the side length of the square is odd. Because any odd number can be written as 2k+1, we can define the size of a square as k, meaning its side length is 2k+1. We now use the following rules to define a pattern made up of squares:

1. The largest square has a size of k (meaning side length 2k+1) and is placed centrally within a square of size 1024. (This means the entire usable area is a square with side length 2049; in terms of coordinates, the top-left corner is at (0,0) and the bottom-right corner is at (2048,2048)).
2. The allowed size of a square is at least 1 and at most 512. Therefore, 1<= k <= 512.
3. Every square with k > 1 has, at each of its four corners, a square whose size is k div 2 (where div represents integer division, e.g., 9 div 2 = 4).

Given a value of k, according to the rules above, we can draw a unique pattern. Each point on the screen may fall inside 0 or more squares. (A point is considered inside a square if it lies exactly on the edge as well). So, if the largest square has k=15, we can draw the following pattern:

(as illustrated)

Write a program that reads in k and the coordinates of a point, then outputs the total number of squares that enclose that point.

### Input

Each test case consists of a line with 3 integers, representing k and the coordinates of a point. The last line consists of three zeros, indicating the end of input.

### Output

For each test case, output a single line showing the total number of squares that enclose the point. The output should be right-aligned and have a length of 3.

## Sample Input

```
500 113 941
0 0 0
```

## Sample Output

```
  5
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
