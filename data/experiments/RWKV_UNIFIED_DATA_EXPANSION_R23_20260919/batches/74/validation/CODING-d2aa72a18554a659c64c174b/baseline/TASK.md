We have N continuous random variables X_1,X_2,\dots,X_N. X_i has a continuous uniform distribution over the interval \lbrack L_i, R_i \rbrack.
Let E be the expected value of the K-th greatest value among the N random variables. Print E \bmod {998244353} as specified in Notes.

Input

Input is given from Standard Input in the following format:
N K
L_1 R_1
L_2 R_2
\vdots
L_N R_N

Output

Print E \bmod {998244353}.

Constraints


- 1 \leq N \leq 50
- 1 \leq K \leq N
- 0 \leq L_i \lt R_i \leq 100
- All values in input are integers.

Sample Input 1

1 1
0 2

Sample Output 1

1

The answer is the expected value of the random variable with a continuous uniform distribution over the interval \lbrack 0, 2 \rbrack. Thus, we should print 1.

Sample Input 2

2 2
0 2
1 3

Sample Output 2

707089751

The answer represented as a rational number is \frac{23}{24}. We have 707089751 \times 24 \equiv 23 \pmod{998244353}, so we should print 707089751.

Sample Input 3

10 5
35 48
44 64
47 59
39 97
36 37
4 91
38 82
20 84
38 50
39 69

Sample Output 3

810056397

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
