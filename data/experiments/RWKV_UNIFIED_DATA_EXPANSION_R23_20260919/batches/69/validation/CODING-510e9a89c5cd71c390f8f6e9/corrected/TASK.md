Read problems statements in [Russian].

We define the *GCD set* of an array A of length N as the set containing the GCD of all prefixes of A. More formally, the GCD set G of A contains the values \gcd([A_{1}]), \gcd([A_{1}, A_{2}]), \gcd([A_{1}, A_{2}, A_{3}]), \ldots, \gcd([A_{1}, A_{2}, \ldots, A_{n}]), where \gcd(B) is the largest integer d such that all the numbers in array B are divisible by d. Note that all values in G are distinct.

For example, \gcd([6]) = 6, \gcd([6, 12]) = 6, \gcd([6, 12, 9]) = 3, and \gcd([6, 12, 9, 2]) = 1. Therefore, the GCD set of the array [6, 12, 9, 2] is \{1, 3, 6\}.

You are given an integer set S of size M and two integers N, MOD, where MOD is a prime. You need to calculate the probability that the GCD set of P is equal to S, where P is a permutation of values 1 to N chosen uniformly randomly.

It can be shown that the answer is in the form of \frac{P}{Q} where P and Q are coprime non-negative integers and Q \neq 0. You need to find the value P \cdot Q^{-1} \pmod{MOD}.

------ Input Format ------ 

- The first line contains an integer T denoting the number of test cases. The T test cases then follow.
- The first line of each test case contains three integers N, M, MOD denoting the length of the permutation, the size of the given integer set, and the modulo respectively.
- The second line of each test case contains m integers in increasing order S_{1}, S_{2}, \ldots, S_{M} representing the given integer set.

------ Output Format ------ 

For each test case, output on one line an integer equals to the answer of that test case.

------ Constraints ------ 

$1 ≤T ≤10$
$1 ≤N ≤10^{9}$
$1 ≤ M ≤ 2 \cdot 10^{4}$
$10^{9} < MOD < 2 \cdot 10^{9}$
$MOD$ is a prime
$1 ≤ S_{1} < S_{2} < \ldots < S_{M} ≤ N$

----- Sample Input 1 ------ 
4
4 3 1000000007
1 2 4
9 2 1000000009
1 3
10 3 1000000007
2 4 8
864197532 5 1876248763
1 4019 727439 19640853 864197532

----- Sample Output 1 ------ 
83333334
888888897
0
1828476640
----- explanation 1 ------ 
- For the first test case, there are 2 permutations that satisfy the condition:

1. $[4, 2, 1, 3]$

2. $[4, 2, 3, 1]$

Since there are $4!$ permutations of length $4$ in total, the probability is $\frac{2}{4!} = \frac{1}{12}$. As $83333334 \cdot 12 \equiv 1 \pmod {10^{9} + 7}$, we output $83333334$.

- For the second test case, the probability is $\frac{1}{9}$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
