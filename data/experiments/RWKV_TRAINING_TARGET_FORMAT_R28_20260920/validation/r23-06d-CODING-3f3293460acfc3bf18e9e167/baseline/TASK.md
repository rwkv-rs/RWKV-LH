William has a favorite bracket sequence. Since his favorite sequence is quite big he provided it to you as a sequence of positive integers c_1, c_2, ..., c_n where c_i is the number of consecutive brackets "(" if i is an odd number or the number of consecutive brackets ")" if i is an even number.

For example for a bracket sequence "((())()))" a corresponding sequence of numbers is [3, 2, 1, 3].

You need to find the total number of continuous subsequences (subsegments) [l, r] (l ≤ r) of the original bracket sequence, which are regular bracket sequences.

A bracket sequence is called regular if it is possible to obtain correct arithmetic expression by inserting characters "+" and "1" into this sequence. For example, sequences "(())()", "()" and "(()(()))" are regular, while ")(", "(()" and "(()))(" are not.

Input

The first line contains a single integer n (1 ≤ n ≤ 1000), the size of the compressed sequence.

The second line contains a sequence of integers c_1, c_2, ..., c_n (1 ≤ c_i ≤ 10^9), the compressed sequence.

Output

Output a single integer — the total number of subsegments of the original bracket sequence, which are regular bracket sequences.

It can be proved that the answer fits in the signed 64-bit integer data type.

Examples

Input


5
4 1 2 3 1


Output


5


Input


6
1 3 2 1 2 4


Output


6


Input


6
1 1 1 1 2 2


Output


7

Note

In the first example a sequence (((()(()))( is described. This bracket sequence contains 5 subsegments which form regular bracket sequences:

  1. Subsequence from the 3rd to 10th character: (()(()))
  2. Subsequence from the 4th to 5th character: ()
  3. Subsequence from the 4th to 9th character: ()(())
  4. Subsequence from the 6th to 9th character: (())
  5. Subsequence from the 7th to 8th character: ()



In the second example a sequence ()))(()(()))) is described.

In the third example a sequence ()()(()) is described.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
