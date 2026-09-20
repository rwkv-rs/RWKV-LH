Mahmoud has an array a consisting of n integers. He asked Ehab to find another array b of the same length such that: b is lexicographically greater than or equal to a . b i  ≥ 2 . b is pairwise coprime: for every 1 ≤  i  <  j  ≤  n , b i and b j are coprime, i. e. GCD ( b i ,  b j ) = 1 , where GCD ( w ,  z ) is the greatest common divisor of w and z . Ehab wants to choose a special array so he wants the lexicographically minimal array between all the variants. Can you find it? An array x is lexicographically greater than an array y if there exists an index i such than x i  >  y i and x j  =  y j for all 1 ≤  j  <  i . An array x is equal to an array y if x i  =  y i for all 1 ≤  i  ≤  n .

## Time Limit and Memory Limit

Time Limit: 3 seconds
Memory Limit: 256 megabytes

## Input Specification

The first line contains an integer n (1 ≤  n  ≤ 10 5 ) , the number of elements in a and b . The second line contains n integers a 1 , a 2 , ... , a n (2 ≤  a i  ≤ 10 5 ) , the elements of a .

## Output Specification

Output n space-separated integers, the i -th of them representing b i .

## Examples

### Input #1
5
2 3 5 4 13

### Output #1
2 3 5 7 11 

### Input #2
3
10 3 7

### Output #2
10 3 7

## Note

Note that in the second sample, the array is already pairwise coprime so we printed it.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
