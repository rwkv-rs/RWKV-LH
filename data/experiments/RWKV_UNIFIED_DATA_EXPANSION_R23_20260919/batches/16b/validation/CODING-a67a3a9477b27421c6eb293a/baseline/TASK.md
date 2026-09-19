Given is a string S consisting of Y and ..
You can do the following operation on S between 0 and K times (inclusive).

- Swap two adjacent characters in S.

What is the maximum possible number of consecutive Ys in S after the operations?

Input

Input is given from Standard Input in the following format:
S
K

Output

Print the answer.

Constraints


- 2 \leq |S| \leq 2 \times 10^5
- Each character of S is Y or ..
- 0 \leq K \leq 10^{12}
- K is an integer.

Sample Input 1

YY...Y.Y.Y.
2

Sample Output 1

3

After swapping the 6-th, 7-th characters, and 9-th, 10-th characters, we have YY....YYY.., which has three consecutive Ys at 7-th through 9-th positions.
We cannot have four or more consecutive Ys, so the answer is 3.

Sample Input 2

YYYY....YYY
3

Sample Output 2

4

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
