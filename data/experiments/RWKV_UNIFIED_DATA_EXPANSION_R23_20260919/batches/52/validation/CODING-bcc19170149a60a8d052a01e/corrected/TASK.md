We have a bipartite graph with L vertices to the left and R vertices to the right.
Takahashi will install surveillance cameras in these vertices.
Installing cameras incurs the following cost.

- A_i yen (the Japanese currency) for each camera installed in the i-th (1 \le i \le L) vertex to the left;
- B_j yen (the Japanese currency) for each camera installed in the j-th (1 \le j \le R) vertex to the right.

It is allowed to install multiple cameras on the same vertex.
Find the minimum amount of money needed to install cameras to satisfy the following condition.

- For every pair of integers (i, j) such that 1 \le i \le L, 1 \le j \le R, there is a total of C_{i,j} or more cameras installed in the i-th vertex to the left and j-th vertex to the right.

Input

Input is given from Standard Input in the following format:
L R
A_1 A_2 \dots A_L
B_1 B_2 \dots B_R
C_{1,1} C_{1,2} \dots C_{1,R}
C_{2,1} C_{2,2} \dots C_{2,R}
\vdots
C_{L,1} C_{L,2} \dots C_{L,R}

Output

Print the answer as an integer.

Constraints


- All values in input are integers.
- 1 \le L,R \le 100
- 1 \le A_i,B_i \le 10
- 0 \le C_{i,j} \le 100

Sample Input 1

3 4
4 3 6
5 2 3 4
1 2 3 2
2 1 2 3
3 2 1 2

Sample Output 1

37

You can achieve the objective for 37 yen as follows, which is the minimum amount required.

- Install 2 cameras on the 1-st vertex in the left.
- Install 3 cameras on the 2-nd vertex in the left.
- Install 2 cameras on the 3-rd vertex in the left.
- Install 1 camera on the 1-st vertex in the right.
- Install 1 camera on the 3-rd vertex in the right.

Sample Input 2

1 1
10
10
0

Sample Output 2

0

No camera may be needed.

Sample Input 3

5 6
3 2 6 7 5
4 9 8 6 2 3
2 0 2 1 1 0
2 3 2 1 0 0
2 2 4 0 2 2
4 1 0 3 0 2
1 0 0 2 2 5

Sample Output 3

79

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
