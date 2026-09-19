We have a rectangular room that is H meters long and W meters wide.
We will fill this entire room with tatami (rectangular mats) that are 2 meters long and 1 meter wide, and hanjo (square mats) that are 1 meter long and 1 meter wide. Each tatami can be placed vertically or horizontally.
How many ways are there to fill the room?
We distinguish ways that match only after rotation or reflection.  
Since the count can be enormous, find it modulo 998244353.

Input

Input is given from Standard Input in the following format:
H W

Output

Print the answer.

Constraints


- 1 \leq H \leq 6
- 1 \leq W \leq 10^{12}

Sample Input 1

2 2

Sample Output 1

7

We have the following seven ways:

Sample Input 2

3 3

Sample Output 2

131

Sample Input 3

5 100

Sample Output 3

379944232

Be sure to find the count modulo 998244353.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
