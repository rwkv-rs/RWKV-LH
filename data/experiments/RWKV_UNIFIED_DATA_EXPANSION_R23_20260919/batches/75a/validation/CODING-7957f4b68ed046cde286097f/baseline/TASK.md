You are given a tree with N vertices numbered 1, 2, ..., N. The i-th edge connects Vertex a_i and Vertex b_i. You are also given a string S of length N consisting of `0` and `1`. The i-th character of S represents the number of pieces placed on Vertex i.

Snuke will perform the following operation some number of times:

* Choose two pieces the distance between which is at least 2, and bring these pieces closer to each other by 1. More formally, choose two vertices u and v, each with one or more pieces, and consider the shortest path between them. Here the path must contain at least two edges. Then, move one piece from u to its adjacent vertex on the path, and move one piece from v to its adjacent vertex on the path.



By repeating this operation, Snuke wants to have all the pieces on the same vertex. Is this possible? If the answer is yes, also find the minimum number of operations required to achieve it.

Constraints

* 2 \leq N \leq 2000
* |S| = N
* S consists of `0` and `1`, and contains at least one `1`.
* 1 \leq a_i, b_i \leq N(a_i \neq b_i)
* The edges (a_1, b_1), (a_2, b_2), ..., (a_{N - 1}, b_{N - 1}) forms a tree.
Input

Input is given from Standard Input in the following format:


N
S
a_1 b_1
a_2 b_2
:
a_{N - 1} b_{N - 1}


Output

If it is impossible to have all the pieces on the same vertex, print `-1`. If it is possible, print the minimum number of operations required.

Examples

Input

7
0010101
1 2
2 3
1 4
4 5
1 6
6 7


Output

3


Input

7
0010110
1 2
2 3
1 4
4 5
1 6
6 7


Output

-1


Input

2
01
1 2


Output

0

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
