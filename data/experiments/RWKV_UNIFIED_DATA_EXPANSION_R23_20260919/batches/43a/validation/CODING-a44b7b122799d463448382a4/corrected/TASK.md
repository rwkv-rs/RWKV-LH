Given are permutations of (1, \dots, N): p = (p_1, \dots, p_N) and q = (q_1, \dots, q_N).
Find the number, modulo (10^9 + 7), of permutations r = (r_1, \dots, r_N) of (1, \dots, N) such that r_i \neq p_i and r_i \neq q_i for every i (1 \leq i \leq N).

Input

Input is given from Standard Input in the following format:
N
p_1 \ldots p_N
q_1 \ldots q_N

Output

Print the answer.

Constraints


- 1 \leq N \leq 3000
- 1 \leq p_i, q_i \leq N
- p_i \neq p_j \, (i \neq j)
- q_i \neq q_j \, (i \neq j)
- All values in input are integers.

Sample Input 1

4
1 2 3 4
2 1 4 3

Sample Output 1

4

There are four valid permutations: (3, 4, 1, 2), (3, 4, 2, 1), (4, 3, 1, 2), and (4, 3, 2, 1).

Sample Input 2

3
1 2 3
2 1 3

Sample Output 2

0

The answer may be 0.

Sample Input 3

20
2 3 15 19 10 7 5 6 14 13 20 4 18 9 17 8 12 11 16 1
8 12 4 13 19 3 10 16 11 9 1 2 17 6 5 18 7 14 20 15

Sample Output 3

803776944

Be sure to print the count modulo (10^9 + 7).

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
