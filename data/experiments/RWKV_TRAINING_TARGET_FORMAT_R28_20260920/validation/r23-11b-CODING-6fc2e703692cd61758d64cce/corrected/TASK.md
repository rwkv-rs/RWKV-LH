How many ways are there to arrange N white balls and M black balls in a row from left to right to satisfy the following condition?

- For each i (1 \leq i \leq N + M), let w_i and b_i be the number of white balls and black balls among the leftmost i balls, respectively. Then, w_i \leq b_i + K holds for every i.

Since the count can be enormous, find it modulo (10^9 + 7).

Input

Input is given from Standard Input in the following format:
N M K

Output

Print the answer. Be sure to find the count modulo (10^9 + 7).

Constraints


- 0 \leq N, M \leq 10^6
- 1 \leq N + M
- 0 \leq K \leq N
- All values in input are integers.

Sample Input 1

2 3 1

Sample Output 1

9

There are 10 ways to arrange 2 white balls and 3 black balls in a row, as shown below, where w and b stand for a white ball and a black ball, respectively.
wwbbb
wbwbb
wbbwb
wbbbw
bwwbb
bwbwb
bwbbw
bbwwb
bbwbw
bbbww
Among them, wwbbb is the only one that does not satisfy the condition. Here, there are 2 white balls and 0 black balls among the 2 leftmost balls, and we have 2 > 0 + K = 1.

Sample Input 2

1 0 0

Sample Output 2

0

There may be no way to satisfy the condition.

Sample Input 3

1000000 1000000 1000000

Sample Output 3

192151600

Be sure to print the count modulo (10^9 + 7).

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
