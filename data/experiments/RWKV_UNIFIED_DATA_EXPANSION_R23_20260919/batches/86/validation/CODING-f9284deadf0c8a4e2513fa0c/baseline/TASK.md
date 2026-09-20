Find the number of graphs with N labeled vertices and M unlabeled edges, not necessarily simple or connected, that satisfy the following conditions, modulo (10^9+7):

- There is no self-loop;
- The degree of every vertex is at most 2;
- The maximum of the sizes of the connected components is exactly L.

Input

Input is given from Standard Input in the following format:
N M L

Output

Print the answer.

Constraints


- 2 \leq N \leq 300
- 1\leq M \leq N
- 1 \leq L \leq N
- All values in input are integers.

Sample Input 1

3 2 3

Sample Output 1

3

When the vertices are labeled 1 through N, the following three graphs satisfy the condition:

- The graph with edges 1-2 and 2-3;
- The graph with edges 1-2 and 1-3;
- The graph with edges 1-3 and 2-3.

Sample Input 2

4 3 2

Sample Output 2

6

Sample Input 3

300 290 140

Sample Output 3

211917445

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
