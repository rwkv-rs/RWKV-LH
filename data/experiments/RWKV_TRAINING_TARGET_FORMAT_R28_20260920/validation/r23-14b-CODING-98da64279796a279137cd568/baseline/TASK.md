You are given a directed graph with N vertices and M edges. The vertices are numbered 1 through N, and the edges are numbered 1 through M. Edge i (1 \leq i \leq M) goes from Vertex s_i to Vertex t_i and has a length of 1.
For each i (1 \leq i \leq M), find the shortest distance from Vertex 1 to Vertex N when all edges except Edge i are passable, or print -1 if Vertex N is unreachable from Vertex 1.

Input

Input is given from Standard Input in the following format:
N M
s_1 t_1
s_2 t_2
\vdots
s_M t_M

Output

Print M lines.
The i-th line should contain the shortest distance from Vertex 1 to Vertex N when all edges except Edge i are passable, or -1 if Vertex N is unreachable from Vertex 1.

Constraints


- 2 \leq N \leq 400
- 1 \leq M \leq N(N-1)
- 1 \leq s_i,t_i \leq N
- s_i \neq t_i
- (s_i,t_i) \neq (s_j,t_j) (i \neq j)
- All values in input are integers.

Sample Input 1

3 3
1 2
1 3
2 3

Sample Output 1

1
2
1

Sample Input 2

4 4
1 2
2 3
2 4
3 4

Sample Output 2

-1
2
3
2

Vertex N is unreachable from Vertex 1 when all edges except Edge 1 are passable, so the corresponding line contains -1.

Sample Input 3

5 10
1 2
1 4
1 5
2 1
2 3
3 1
3 2
3 5
4 2
4 3

Sample Output 3

1
1
3
1
1
1
1
1
1
1

Sample Input 4

4 1
1 2

Sample Output 4

-1

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
