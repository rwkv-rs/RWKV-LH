Miki is a high school student. She has a part time job, so she cannot take enough sleep on weekdays. She wants to take good sleep on holidays, but she doesn't know the best length of sleeping time for her. She is now trying to figure that out with the following algorithm:

1. Begin with the numbers K, R and L.
2. She tries to sleep for H=(R+L)/2 hours.
3. If she feels the time is longer than or equal to the optimal length, then update L with H. Otherwise, update R with H.
4. After repeating step 2 and 3 for K nights, she decides her optimal sleeping time to be T' = (R+L)/2.



If her feeling is always correct, the steps described above should give her a very accurate optimal sleeping time. But unfortunately, she makes mistake in step 3 with the probability P.

Assume you know the optimal sleeping time T for Miki. You have to calculate the probability PP that the absolute difference of T' and T is smaller or equal to E. It is guaranteed that the answer remains unaffected by the change of E in 10^{-10}.
Input

The input follows the format shown below

K R L
P
E
T


Where the integers 0 \leq K \leq 30, 0 \leq R \leq L \leq 12 are the parameters for the algorithm described above. The decimal numbers on the following three lines of the input gives the parameters for the estimation. You can assume 0 \leq P \leq 1, 0 \leq E \leq 12, 0 \leq T \leq 12.

Output

Output PP in one line. The output should not contain an error greater than 10^{-5}.

Examples

Input

3 0 2
0.10000000000
0.50000000000
1.00000000000


Output

0.900000


Input

3 0 2
0.10000000000
0.37499999977
1.00000000000


Output

0.810000


Input

3 0 2
0.10000000000
0.00000100000
0.37500000000


Output

0.729000


Input

3 0 2
0.20000000000
0.00000100000
0.37500000000


Output

0.512000

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
