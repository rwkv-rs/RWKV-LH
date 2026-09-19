Bob has a favorite number k and a i of length n . Now he asks you to answer m queries. Each query is given by a pair l i and r i and asks you to count the number of pairs of integers i and j , such that l  ≤  i  ≤  j  ≤  r and the xor of the numbers a i ,  a i  + 1 , ...,  a j is equal to k .

## Time Limit and Memory Limit

Time Limit: 4 seconds
Memory Limit: 256 megabytes

## Input Specification

The first line of the input contains integers n , m and k ( 1 ≤  n ,  m  ≤ 100 000 , 0 ≤  k  ≤ 1 000 000 ) — the length of the array, the number of queries and Bob's favorite number respectively. The second line contains n integers a i ( 0 ≤  a i  ≤ 1 000 000 ) — Bob's array. Then m lines follow. The i -th line contains integers l i and r i ( 1 ≤  l i  ≤  r i  ≤  n ) — the parameters of the i -th query.

## Output Specification

Print m lines, answer the queries in the order they appear in the input.

## Examples

### Input #1
6 2 3
1 2 1 1 0 3
1 6
3 5

### Output #1
7
0

### Input #2
5 3 1
1 1 1 1 1
1 5
2 4
1 3

### Output #2
9
4
4

## Note

In the first sample the suitable pairs of i and j for the first query are: ( 1 , 2 ), ( 1 , 4 ), ( 1 , 5 ), ( 2 , 3 ), ( 3 , 6 ), ( 5 , 6 ), ( 6 , 6 ). Not a single of these pairs is suitable for the second query. In the second sample xor equals 1 for all subarrays of an odd length.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
