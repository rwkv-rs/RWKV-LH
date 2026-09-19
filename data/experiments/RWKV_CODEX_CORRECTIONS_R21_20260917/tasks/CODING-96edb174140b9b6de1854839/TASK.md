Tapan and Divya have a rectangular shaped chocolate bar with chocolates labeled T, D and U. They want to split the bar into exactly two pieces such that:

Tapan's piece can not contain any chocolate labeled D and similarly, Divya's piece can not contain any chocolate labeled T. All chocolates in each piece must be connected (two chocolates are connected if they share an edge), i.e. the chocolates should form one connected component.

The absolute difference between the number of chocolates in pieces should be at most K.

In any piece, there should not be 4 adjacent chocolates that form a square, i.e. there should not be a fragment like this:

XX
XX
Input Format

The first line of the input contains 3 integers M, N and K separated by a single space.
M lines follow, each of which contains N characters. Each character is 'T','D' or 'U'.

Constraints

0≤ M, N ≤8
0≤ K ≤ M * N

Output Format

A single line containing the number of ways to divide the chocolate bar.

SAMPLE INPUT
2 2 4
UU
UU

SAMPLE OUTPUT
12

Explanation

There are 24 = 16 possible separations. The 4 invalid are:

TT

TT
DD

DD
DT

TD
TD

DT

Some of the valid ones are:

TD

TD
TT

DD
DD

TT
DT

DT

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
