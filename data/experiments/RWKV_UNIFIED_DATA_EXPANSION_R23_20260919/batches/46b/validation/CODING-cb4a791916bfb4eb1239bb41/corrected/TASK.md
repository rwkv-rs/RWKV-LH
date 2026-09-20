There is a grid with H horizontal rows and W vertical columns, where each square contains a digit between 1 and 9.
For each pair of integers (i, j) such that 1 \leq i \leq H and 1 \leq j \leq W, the digit written on the square at the i-th row from the top and j-th column from the left is c_{i, j}.
Using this grid, Takahashi and Aoki will play together.
First, Takahashi chooses a square and puts a piece on it.
Then, the two will repeat the following procedures, 1. through 4., N times.

- Takahashi does one of the following two actions.
- Move the piece to another square that shares a row with the square the piece is on.
- Do nothing.


- Takahashi writes on a blackboard the digit written on the square the piece is on.
- Aoki does one of the following two actions.
- Move the piece to another square that shares a column with the square the piece is on.
- Do nothing.


- Aoki writes on the blackboard the digit written on the square the piece is on.

After that, there will be 2N digits written on the blackboard. Let d_1, d_2, \ldots, d_{2N} be those digits, in the order they are written.
The two boys will concatenate the 2N digits in this order to make a 2N-digit integer X := d_1d_2\ldots d_{2N}.
Find the number, modulo 998244353, of different integers that X can become.

Input

Input is given from Standard Input in the following format:
H W N
c_{1, 1}c_{1, 2}\cdotsc_{1, W}
c_{2, 1}c_{2, 2}\cdotsc_{2, W}
\vdots
c_{H, 1}c_{H, 2}\cdotsc_{H, W}

Output

Print the number, modulo 998244353, of different integers that X can become.

Constraints


- 2 \leq H, W \leq 10
- 1 \leq N \leq 300
- 1 \leq c_{i, j} \leq 9
- All values in input are integers.

Sample Input 1

2 2 1
31
41

Sample Output 1

5

Below is one possible scenario.

- First, Takahashi puts the piece on (1, 2).
- Takahashi moves the piece from (1, 2) to (1, 1), and then writes the digit 3 written on (1, 1).
- Aoki moves the piece from (1, 1) to (2, 1), and then writes the digit 4 written on (2, 1).

In this case, we have X = 34.
Below is another possible scenario.

- First, Takahashi puts the piece on (2, 2).
- Takahashi keeps the piece on (2, 2), and then writes the digit 1 written on (2, 2).
- Aoki moves the piece from (2, 2) to (1, 2), and then writes the digit 1 written on (1, 2).

In this case, we have X = 11.
Other than these, X can also become 33, 44, or 43, but nothing else.
That is, there are five integers that X can become, so we print 5.

Sample Input 2

2 3 4
777
777

Sample Output 2

1

X can only become 77777777.

Sample Input 3

10 10 300
3181534389
4347471911
4997373645
5984584273
1917179465
3644463294
1234548423
6826453721
5892467783
1211598363

Sample Output 3

685516949

Be sure to find the count modulo 998244353.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
