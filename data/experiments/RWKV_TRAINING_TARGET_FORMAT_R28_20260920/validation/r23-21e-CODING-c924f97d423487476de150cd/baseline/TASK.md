In the xy-plane, we have N points numbered 1 through N.
Point i is at the coordinates (X_i,Y_i). Any two different points are at different positions.
Find the number of ways to choose three of these N points so that connecting the chosen points with segments results in a triangle with a positive area.

Input

Input is given from Standard Input in the following format:
N
X_1 Y_1
X_2 Y_2
\dots
X_N Y_N

Output

Print the answer as an integer.

Constraints


- All values in input are integers.
- 3 \le N \le 300
- -10^9 \le X_i,Y_i \le 10^9
- (X_i,Y_i) \neq (X_j,Y_j) if i \neq j.

Sample Input 1

4
0 1
1 3
1 1
-1 -1

Sample Output 1

3

The figure below illustrates the points.

There are three ways to choose points that form a triangle: \{1,2,3\},\{1,3,4\},\{2,3,4\}.

Sample Input 2

20
224 433
987654321 987654321
2 0
6 4
314159265 358979323
0 0
-123456789 123456789
-1000000000 1000000000
124 233
9 -6
-4 0
9 5
-7 3
333333333 -333333333
-9 -1
7 -10
-1 5
324 633
1000000000 -1000000000
20 0

Sample Output 2

1124

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
