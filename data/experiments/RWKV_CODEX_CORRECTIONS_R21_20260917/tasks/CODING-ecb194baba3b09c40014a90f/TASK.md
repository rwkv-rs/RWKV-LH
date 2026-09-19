Stick n circular stickers with a radius of 1 on a square origami paper with a side length of 10. The stickers can be stacked. Create a program that reads the coordinates of the position where the stickers are to be attached and outputs the number of stickers at the place where the stickers overlap most on the origami paper (assuming that even one sticker "overlaps"). ..

Gives the x and y coordinates with the lower left corner of the origami as the origin. Let's put the sticker with these x and y as the center of the circle. The center of the circle never goes out of the origami. Also, multiple stickers will not be attached at the same coordinates.

Hint

It is a figure with a sticker attached as shown in the
input example. The circle represents the sticker, and the number represents the number of lines in the input example. At point (2.3, 4.6), the four stickers on the second, third, sixth, and tenth lines of the input example overlap.

<image>

The distance between the centers of 6 and 9 is 2.01293, so the seals do not overlap. The distance between the centers of 1 and 12 is 1.98231, so the seals overlap.

When two circles are in contact (when the distance between the centers is 2), they are assumed to overlap.



Input

Given multiple datasets. Each dataset is given in the following format:


n
x1, y1
x2, y2
::
xn, yn


The first line gives the number of stickers n (0 ≤ 100). The next n lines give the center coordinates of each seal. xi and yi represent the x and y coordinates of the center of the i-th sticker. Each value is given as a real number, including up to 6 digits after the decimal point.

When n is 0, it is the end of the input. The number of datasets does not exceed 50.

Output

For each data set, output the number of stickers (integer) at the place where the stickers overlap most on the origami paper.

Example

Input

15
3.14979,8.51743
2.39506,3.84915
2.68432,5.39095
5.61904,9.16332
7.85653,4.75593
2.84021,5.41511
1.79500,8.59211
7.55389,8.17604
4.70665,4.66125
1.63470,4.42538
7.34959,4.61981
5.09003,8.11122
5.24373,1.30066
0.13517,1.83659
7.57313,1.58150
0


Output

4

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
