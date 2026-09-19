There are N positive integers arranged in a circle.

Now, the i-th number is A_i. Takahashi wants the i-th number to be B_i. For this objective, he will repeatedly perform the following operation:

* Choose an integer i such that 1 \leq i \leq N.
* Let a, b, c be the (i-1)-th, i-th, and (i+1)-th numbers, respectively. Replace the i-th number with a+b+c.



Here the 0-th number is the N-th number, and the (N+1)-th number is the 1-st number.

Determine if Takahashi can achieve his objective. If the answer is yes, find the minimum number of operations required.

Constraints

* 3 \leq N \leq 2 \times 10^5
* 1 \leq A_i, B_i \leq 10^9
* All values in
input are integers.

Input

Input is given from Standard Input in the following format:


N
A_1 A_2 ... A_N
B_1 B_2 ... B_N


Output

Print the minimum number of operations required, or `-1` if the objective cannot be achieved.

Examples

Input

3
1 1 1
13 5 7


Output

4


Input

4
1 2 3 4
2 3 4 5


Output

-1


Input

5
5 6 5 2 1
9817 1108 6890 4343 8704


Output

25

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
