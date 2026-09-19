Arrange integers (0 or more and 99 or less) in a rhombus as illustrated in Fig. 1. Create a program that reads the data representing the rhombus and outputs the maximum value of the sum of the integers that pass when starting from the top and proceeding to the bottom according to the following rules.

* At each step, you can proceed to the lower left diagonal or the lower right diagonal.



For example, in the example of Fig. 1, as shown in Fig. 2, when 7,3,8,7,5,7,8,3,7 is selected and passed, the sum is the maximum 55 (7 + 3 + 8). + 7 + 5 + 7 + 8 + 3 + 7 = 55).



Input

As shown in the input example, a comma-separated sequence of integers is given to the diamond. Each line does not contain whitespace. The input example corresponds to Fig. 1. There are less than 100 rows of data.

Output

Outputs the maximum value of the sum of integers that pass according to the rules on one line.

Example

Input

7
3,8
8,1,0
2,7,4,4
4,5,2,6,5
2,7,4,4
8,1,0
3,8
7


Output

55

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
