A dragon symbolizes wisdom, power and wealth. On Lunar New Year's Day, people model a dragon with bamboo strips and clothes, raise them with rods, and hold the rods high and low to resemble a flying dragon. A performer holding the rod low is represented by a 1 , while one holding it high is represented by a 2 . Thus, the line of performers can be represented by a sequence a 1 ,  a 2 , ...,  a n . Little Tommy is among them. He would like to choose an interval [ l ,  r ] ( 1 ≤  l  ≤  r  ≤  n ), then reverse a l ,  a l  + 1 , ...,  a r so that the length of the longest non-decreasing subsequence of the new sequence is maximum. A non-decreasing subsequence is a sequence of indices p 1 ,  p 2 , ...,  p k , such that p 1  <  p 2  < ... <  p k and a p 1  ≤  a p 2  ≤ ... ≤  a p k . The length of the subsequence is k .

## Time Limit and Memory Limit

Time Limit: 1 second
Memory Limit: 256 megabytes

## Input Specification

The first line contains an integer n (1 ≤  n  ≤ 2000) , denoting the length of the original sequence. The second line contains n space-separated integers, describing the original sequence a 1 ,  a 2 , ...,  a n (1 ≤  a i  ≤ 2,  i  = 1, 2, ...,  n ) .

## Output Specification

Print a single integer, which means the maximum possible length of the longest non-decreasing subsequence of the new sequence.

## Examples

### Input #1
4
1 2 1 2

### Output #1
4

### Input #2
10
1 1 2 2 2 1 1 2 2 1

### Output #2
9

## Note

In the first example, after reversing [2, 3] , the array will become [1, 1, 2, 2] , where the length of the longest non-decreasing subsequence is 4 . In the second example, after reversing [3, 7] , the array will become [1, 1, 1, 1, 2, 2, 2, 2, 2, 1] , where the length of the longest non-decreasing subsequence is 9 .

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
