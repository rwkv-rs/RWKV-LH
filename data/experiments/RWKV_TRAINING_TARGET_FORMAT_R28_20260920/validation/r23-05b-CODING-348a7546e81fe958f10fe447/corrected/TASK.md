## Problem Description:
Alex is the administrator of an IP network. Each of his clients has a set of individual IP addresses, and he decides to group all IP addresses into the smallest possible IP networks.

Each IP address consists of four parts separated by dots. The format is like a, b, c, d, where each part is a decimal number (0 ≤ this number ≤ 255) without any extra leading zeros.

An IP network is defined by two numbers, each with four parts—a network address and a network mask. The network address and network mask are written in the same way as an IP address. To understand the meaning of the network address and network mask, we represent them in binary. The IP address, network address, and network mask each consist of 32 bits: 8 bits for a (from most significant to least significant), followed by 8 bits for b, then 8 bits for c, and finally 8 bits for d.

An IP network includes a range of 2^n IP addresses, where 0 ≤ n ≤ 32. The network mask always has the first 32-n parts set to one, and the last n parts set to zero in the binary representation. The network address has arbitrary first 32-n parts, and the last n parts set to zero in its binary representation. The IP network contains all IP addresses whose first 32-n bits match any 32-n bits of the network address, with all the last bits set to zero.

We say one IP network is smaller than another if it contains fewer IP addresses.

## Input and Output Format
### Input Format:
There are multiple test cases.

The first line of the input contains an integer m. The following m lines each contain an IP address. The IP addresses may be repeated.

### Output Format:
For each test case, write the network address on the first line and the network mask on the second line. The network address and network mask represent the smallest IP network that includes all IP addresses.

## Sample Input and Output:
### Sample Input #1
3

194.85.160.177

194.85.160.183

194.85.160.178

### Sample Output #1
194.85.160.176

255.255.255.248

## Sample Explanation
A network address of an IP network is 194.85.160.176, and its network mask is 255.255.255.248.

This IP network includes 8 IP addresses from 194.85.160.176 to 194.85.160.183.

## Note
0 ≤ n ≤ 32, 1 ≤ m ≤ 1000

Thanks to @BIGmrsrz for the translation.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
