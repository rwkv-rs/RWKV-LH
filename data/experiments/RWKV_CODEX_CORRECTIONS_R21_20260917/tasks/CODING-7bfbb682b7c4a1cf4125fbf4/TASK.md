Problem statement

There are rectangles with vertical and horizontal lengths of h and w, and square squares with a side length of 1 are spread inside. If the upper left cell is (0,0) and the cell to the right of j below (0,0) is represented as (i, j), (i, j) is i + j. If is even, it is painted red, and if it is odd, it is painted blue.

Now, the upper left vertex of (0,0) and the lower right vertex of (h − 1, w − 1) are connected by a line segment. If the length of the red part through which this line segment passes is a and the length of the blue part is b, the ratio a: b is an integer ratio. Express a: b in the simplest way (with relatively prime integers).
input


T
h_1 \ w_1
...
h_T \ w_T


One file contains T inputs. The T in the first line and the vertical and horizontal lengths h_i and w_i in the Tth input are input in the 1 + i line.

Constraint

* An integer
* 1 ≤ T ≤ 1000
* 1 ≤ h_i, w_i ≤ 109



output

Output the answer for each case separated by 1 and separated by spaces. It spans T lines in total.

sample

Sample input 1


3
twenty three
3 3
4 3


Sample output 1


1 1
Ten
1 1


<image>





Example

Input

3
2 3
3 3
4 3


Output

1 1
1 0
1 1

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
