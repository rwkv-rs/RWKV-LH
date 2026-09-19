Senor Vorpal Kickass'o invented an innovative method to encrypt integer sequences of length n. To encrypt a sequence, one has to choose a secret sequence <image>, that acts as a key.

Vorpal is very selective, so the key should be such a sequence bi, that its cyclic shifts are linearly independent, that is, there is no non-zero set of coefficients x0, x1, ..., xn - 1, such that <image> for all k at the same time.

After that for a sequence <image> you should build the following cipher:

<image>

In other words, you are to compute the quadratic deviation between each cyclic shift of bi and the sequence ai. The resulting sequence is the Kickass's cipher. The cipher is in development right now and Vorpal wants to decipher a sequence after it has been encrypted. You are to solve this problem for him. You are given sequences ci and bi. You are to find all suitable sequences ai.

Input

The first line contains a single integer n (<image>).

The second line contains n integers b0, b1, ..., bn - 1 (<image>).

The third line contains n integers c0, c1, ..., cn - 1 (<image>).

It is guaranteed that all cyclic shifts of sequence bi are linearly independent.

Output

In the first line print a single integer k — the number of sequences ai, such that after encrypting them with key bi you get the sequence ci.

After that in each of k next lines print n integers a0, a1, ..., an - 1. Print the sequences in lexicographical order.

Note that k could be equal to 0.

Examples

Input

1
1
0


Output

1
1


Input

1
100
81


Output

2
91
109


Input

3
1 1 3
165 185 197


Output

2
-6 -9 -1
8 5 13

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
