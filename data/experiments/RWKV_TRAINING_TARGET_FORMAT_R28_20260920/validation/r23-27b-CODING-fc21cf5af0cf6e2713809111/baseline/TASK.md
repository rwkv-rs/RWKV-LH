There are N trees standing in a row from left to right. The i-th tree (1 \leq i \leq N) from the left, Tree i, has the height of H_i.
You will now cut down all these N trees in some order you like. Formally, you will choose a permutation P of (1, 2, \ldots, N) and do the operation below for each i=1, 2, 3, ..., N in this order.

- Cut down Tree P_i, that is, set H_{P_i} to 0, at a cost of H_{P_i-1}+H_{P_i}+H_{P_i+1}.

Here, we assume H_0=0,H_{N+1}=0.
In other words, the cost of cutting down a tree is the total height of the tree and the neighboring trees just before doing so.
Find the number of permutations P that minimize the total cost of cutting down the trees. Since the count may be enormous, print it modulo (10^9+7).

Input

Input is given from Standard Input in the following format:
N
H_1 H_2 \ldots H_N

Output

Print the number of permutations P, modulo (10^9+7), that minimize the total cost of cutting down the trees.

Constraints


- 1 \leq N \leq 4000
- 1 \leq H_i \leq 10^9
- All values in input are integers.

Sample Input 1

3
4 2 4

Sample Output 1

2

There are two permutations P that minimize the total cost: (1,3,2) and (3,1,2).
Below, we will show the process of cutting down the trees for P=(1,3,2), for example.

- First, Tree 1 is cut down at a cost of H_0+H_1+H_2=6.
- Next, Tree 3 is cut down at a cost of H_2+H_3+H_4=6.
- Finally, Tree 2 is cut down at a cost of H_1+H_2+H_3=2.

The total cost incurred is 14.

Sample Input 2

3
100 100 100

Sample Output 2

6

Sample Input 3

15
804289384 846930887 681692778 714636916 957747794 424238336 719885387 649760493 596516650 189641422 25202363 350490028 783368691 102520060 44897764

Sample Output 3

54537651

Be sure to print the count modulo (10^9+7).

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
