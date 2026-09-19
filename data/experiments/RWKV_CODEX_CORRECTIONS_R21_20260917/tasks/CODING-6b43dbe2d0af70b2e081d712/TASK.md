We have parcels with five different weights: 1, 2, 3, 4, 5. For each i (1 \leq i \leq 5), there are A_i parcels of weight i.
Additionally, we have people with five different strengths: 1, 2, 3, 4, 5. For each i (1 \leq i \leq 5), there are B_i people with strength i.
Each person can carry any number of parcels (possibly zero), but the total weight of the parcels must not exceed their strength.
You are given T test cases.
For each case, determine whether it is possible for the people to carry all parcels with the appropriate allocation of parcels. That is, determine whether it is possible to allocate each parcel to someone so that each person is allocated parcels whose total weight does not exceed their strength. It is fine to have someone who carries no parcels.

Input

Input is given from Standard Input. The first line contains the number of test cases T:
T

Then, T test cases follow, each in the following format:
A_1 A_2 A_3 A_4 A_5
B_1 B_2 B_3 B_4 B_5

Output

Print T lines.
The i-th line (1\leq i\leq T) should contain Yes if all parcels can be carried in the i-th test case, and No otherwise.

Constraints


- 1 \leq T \leq 5\times 10^4
- 0 \leq A_i,B_i \leq 10^{16}
- 1 \leq A_1+A_2+A_3+A_4+A_5
- 1 \leq B_1+B_2+B_3+B_4+B_5
- All values in input are integers.

Sample Input 1

3
5 1 0 0 1
0 0 0 2 1
0 3 0 0 0
0 0 2 0 0
10000000000000000 0 0 0 0
0 0 0 0 2000000000000000

Sample Output 1

Yes
No
Yes

In the first test case, all parcels can be carried. Here is one way to do so:

- The first person with strength 4 carries four parcels of weight 1.
- The second person with strength 4 carries one parcel of weight 1 and another of weight 2.
- The person with strength 5 carries one parcel of weight 5.

In the second test case, one of the two people with strength 3 has to carry two or more parcels of weight 2, which is impossible.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
