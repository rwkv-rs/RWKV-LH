Given is a string S consisting of K, E, Y.
How many strings are there that can be obtained with at most K swaps of two adjacent characters in S?

Input

Input is given from Standard Input in the following format:
S
K

Output

Print the answer.

Constraints


- 2 \leq |S| \leq 30
- 0 \leq K \leq 10^9
- S consists of K, E, Y.

Sample Input 1

KEY
1

Sample Output 1

3

With at most one swap, there are three strings that can be obtained: KEY, EKY, KYE.

Sample Input 2

KKEE
2

Sample Output 2

4

With at most two swaps, there are four strings that can be obtained: KKEE, KEKE, EKKE, KEEK.

Sample Input 3

KKEEYY
1000000000

Sample Output 3

90

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
