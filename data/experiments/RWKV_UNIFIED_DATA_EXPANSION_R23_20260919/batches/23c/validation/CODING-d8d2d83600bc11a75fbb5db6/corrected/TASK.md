There is a cleaning robot on the square (0, 0) in an infinite two-dimensional grid.
The robot will be given a program represented as a string consisting of four kind of characters L, R, U, D.
It will read the characters in the program from left to right and perform the following action for each character read.

- Let (x, y) be the square where the robot is currently on.
- Make the following move according to the character read:
- if L is read: go to (x-1, y).
- if R is read: go to (x+1, y).
- if U is read: go to (x, y-1).
- if D is read: go to (x, y+1).



You are given a string S consisting of L, R, U, D.
The program that will be executed by the robot is the concatenation of K copies of S.
Squares visited by the robot at least once, including the initial position (0, 0), will be cleaned.
Print the number of squares that will be cleaned at the end of the execution of the program.

Input

Input is given from Standard Input in the following format:
S
K

Output

Print the number of squares that will be cleaned at the end of the execution of the program.

Constraints


- S is a string of length between 1 and 2 \times 10^5 (inclusive) consisting of L, R, U, D.
- 1 \leq K \leq 10^{12}

Sample Input 1

RDRUL
2

Sample Output 1

7

The robot will execute the program RDRULRDRUL. It will start on (0, 0) and travel as follows:
(0, 0) \rightarrow (1, 0) \rightarrow (1, 1) \rightarrow (2, 1) \rightarrow (2, 0) \rightarrow (1, 0) \rightarrow (2, 0) \rightarrow (2, 1) \rightarrow (3, 1) \rightarrow (3, 0) \rightarrow (2, 0).
In the end, seven squares will get cleaned: (0, 0), (1, 0), (1, 1), (2, 0), (2, 1), (3, 0), (3, 1).

Sample Input 2

LR
1000000000000

Sample Output 2

2

Sample Input 3

UUURRDDDRRRUUUURDLLUURRRDDDDDDLLLLLLU
31415926535

Sample Output 3

219911485785

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
