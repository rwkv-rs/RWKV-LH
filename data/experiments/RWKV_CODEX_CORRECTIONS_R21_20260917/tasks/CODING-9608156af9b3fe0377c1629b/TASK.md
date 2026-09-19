There are some cells that can control other cells. If you control some cells, then you also control the cells directly controlled by them. The question is, how many cells do you need to control to be able to control all cells, given that there is a control relationship between each pair of cells?

- You are given n (n ≤ 75) cells.
- Some cells can control others. If you control some cells, you'll also control the cells directly controlled by them.
- There is a control relationship between each pair of cells.

Determine how many cells you need to control to be able to control all the cells.

## Input Format
There are multiple sets of inputs.

The first number, n, is the size of the adjacency matrix.

The following input consists of an n*n matrix.

The element in the i-th row and j-th column indicates the relationship between the i-th element and the j-th element.

A value of 1 means i controls j, and vice versa.

## Output Format
For each set of test data, first output `Case #%d:`

Then, output the minimum number of cells needed to control.

Finally, output which cells are controlled.

## Sample Test
Input

2

00

10

3

010

001

100

5

01000

00011

11001

10100

10010

Output

Case 1: 1 2

Case 2: 2 1 2

Case 3: 2 2 3

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
