You are given an integer N. Consider permuting the digits in N and separate them into two positive integers.
For example, for the integer 123, there are six ways to separate it, as follows:

- 12 and 3,
- 21 and 3,
- 13 and 2,
- 31 and 2,
- 23 and 1,
- 32 and 1.

Here, the two integers after separation must not contain leading zeros. For example, it is not allowed to separate the integer 101 into 1 and 01. Additionally, since the resulting integers must be positive, it is not allowed to separate 101 into 11 and 0, either.
What is the maximum possible product of the two resulting integers, obtained by the optimal separation?

Input

Input is given from Standard Input in the following format:
N

Output

Print the maximum possible product of the two integers after separation.

Constraints


- N is an integer between 1 and 10^9 (inclusive).
- N contains two or more digits that are not 0.

Sample Input 1

123

Sample Output 1

63

As described in Problem Statement, there are six ways to separate it:

- 12 and 3,
- 21 and 3,
- 13 and 2,
- 31 and 2,
- 23 and 1,
- 32 and 1.

The products of these pairs, in this order, are 36, 63, 26, 62, 23, 32, with 63 being the maximum.

Sample Input 2

1010

Sample Output 2

100

There are two ways to separate it:

- 100 and 1,
- 10 and 10.

In either case, the product is 100.

Sample Input 3

998244353

Sample Output 3

939337176

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
