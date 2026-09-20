Alyona has built n towers by putting small cubes some on the top of others. Each cube has size 1 × 1 × 1 . A tower is a non-zero amount of cubes standing on the top of each other. The towers are next to each other, forming a row. Sometimes Alyona chooses some segment towers, and put on the top of each tower several cubes. Formally, Alyouna chooses some segment of towers from l i to r i and adds d i cubes on the top of them. Let the sequence a 1 ,  a 2 , ...,  a n be the heights of the towers from left to right. Let's call as a segment of towers a l ,  a l  + 1 , ...,  a r a hill if the following condition holds: there is integer k ( l  ≤  k  ≤  r ) such that a l  <  a l  + 1  <  a l  + 2  < ... <  a k  >  a k  + 1  >  a k  + 2  > ... >  a r . After each addition of d i cubes on the top of the towers from l i to r i , Alyona wants to know the maximum width among all hills. The width of a hill is the number of towers in it.

## Time Limit and Memory Limit

Time Limit: 2 seconds
Memory Limit: 256 megabytes

## Input Specification

The first line contain single integer n ( 1 ≤  n  ≤ 3·10 5 ) — the number of towers. The second line contain n integers a 1 ,  a 2 , ...,  a n ( 1 ≤  a i  ≤ 10 9 ) — the number of cubes in each tower. The third line contain single integer m ( 1 ≤  m  ≤ 3·10 5 ) — the number of additions. The next m lines contain 3 integers each. The i -th of these lines contains integers l i , r i and d i ( 1 ≤  l  ≤  r  ≤  n , 1 ≤  d i  ≤ 10 9 ), that mean that Alyona puts d i cubes on the tio of each of the towers from l i to r i .

## Output Specification

Print m lines. In i -th line print the maximum width of the hills after the i -th addition.

## Examples

### Input #1
5
5 5 5 5 5
3
1 3 2
2 2 1
4 4 1

### Output #1
2
4
5

## Note

The first sample is as follows: After addition of 2 cubes on the top of each towers from the first to the third, the number of cubes in the towers become equal to [7, 7, 7, 5, 5] . The hill with maximum width is [7, 5] , thus the maximum width is 2 . After addition of 1 cube on the second tower, the number of cubes in the towers become equal to [7, 8, 7, 5, 5] . The hill with maximum width is now [7, 8, 7, 5] , thus the maximum width is 4 . After addition of 1 cube on the fourth tower, the number of cubes in the towers become equal to [7, 8, 7, 6, 5] . The hill with maximum width is now [7, 8, 7, 6, 5] , thus the maximum width is 5 .

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
