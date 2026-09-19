AtCoder in another world holds 10 types of contests called AAC, ..., AJC. There will be N contests from now on.
The types of these N contests are given to you as a string S: if the i-th character of S is x, the i-th contest will be AxC.
AtCoDeer will choose and participate in one or more contests from the N so that the following condition is satisfied.

- In the sequence of contests he will participate in, the contests of the same type are consecutive.
- Formally, when AtCoDeer participates in x contests and the i-th of them is of type T_i, for every triple of integers (i,j,k) such that 1 \le i < j < k \le x, T_i=T_j must hold if T_i=T_k.



Find the number of ways for AtCoDeer to choose contests to participate in, modulo 998244353.
Two ways to choose contests are considered different when there is a contest c such that AtCoDeer participates in c in one way but not in the other.

Input

Input is given from Standard Input in the following format:
N
S

Output

Print the answer as an integer.

Constraints


- 1 \le N \le 1000
- |S|=N
- S consists of uppercase English letters from A through J.

Sample Input 1

4
BGBH

Sample Output 1

13

For example, participating in the 1-st and 3-rd contests is valid, and so is participating in the 2-nd and 4-th contests.
On the other hand, participating in the 1-st, 2-nd, 3-rd, and 4-th contests is invalid, since the participations in ABCs are not consecutive, violating the condition for the triple (i,j,k)=(1,2,3).
Additionally, it is not allowed to participate in zero contests.
In total, there are 13 valid ways to participate in some contests.

Sample Input 2

100
BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBIEIJEIJIJCGCCFGIEBIHFCGFBFAEJIEJAJJHHEBBBJJJGJJJCCCBAAADCEHIIFEHHBGF

Sample Output 2

330219020

Be sure to find the count modulo 998244353.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
