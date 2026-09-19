JYY has a strange calculator. One day, this calculator broke, and JYY hopes you can help him write a program to simulate the operations of this calculator.

## Problem Description

JYY's calculator can execute $N$ preset instructions. Each time JYY inputs a positive integer $X$ into the calculator, the calculator will use $X$ as the initial value and sequentially execute the $N$ preset instructions, then return the final result to JYY.

Each instruction can be one of the following four types (where $a$ represents a positive integer):

1. $+a$: Adds $a$ to the current result.
2. $-a$: Subtracts $a$ from the current result.
3. $\times a$: Multiplies the current result by $a$.
4. $@a$: Adds $a \times X$ to the current result (where $X$ is the initial number input by JYY).

The calculator has a limited storage range for recording the result, so there is an issue of overflow after each calculation.

In JYY's calculator, the variable storing the result can only store positive integers between $L$ and $R$. If the result of an instruction exceeds $R$, the calculator will automatically change the result to $R$ and continue the subsequent calculations with $R$ as the current result. Similarly, if the result is less than $L$, the calculator will change the result to $L$ and continue the calculations.

For example, if the calculator can store values between $1$ and $6$, and the current result is $2$, after executing the $+5$ operation, the value in the result variable will be $6$. Although the actual result of $2+5$ is $7$, since $7$ exceeds the upper limit of the storage range, the result is automatically corrected to the upper limit, which is $6$.

JYY wants to input $Q$ values into the calculator. He wants to know what results will be obtained for each of these $Q$ values?

## Input Format

The first line contains three positive integers, $N$, $L$, and $R$.

The next $N$ lines each contain an instruction, described as in the problem, consisting of a character and a positive integer separated by a space.

The $N+2$nd line contains an integer $Q$, indicating the number of values JYY wants to input.

The next $Q$ lines each contain a positive integer, where the $k$th positive integer $X_k$ represents the integer JYY inputs in the $k$th attempt.

## Output Format

Output $Q$ lines, each containing a positive integer. The $k$th line represents the result obtained after inputting $X_k$ and sequentially executing the $N$ instructions.

## Sample Input and Output

### Input Sample #1

```
5 1 6
+ 5
- 3
* 2
- 7
@ 2
3
2
1
5
```

### Output Sample #1

```
5
3
6
```

## Notes

### Sample Explanation

When JYY inputs $2$, the calculator performs 5 operations, and the result after each operation is $6$ (the actual result is $7$ but exceeds the upper limit), $3, 6, 1$ (the actual result is $-1$ but is below the lower limit), and $5$ (since the initial input was $2$, this calculation is $1 + 2 \times 2$).

### Data Range and Constraints

For all test data, $1 \le N$, $Q \le 10^5$, $1 \le L \le X_k \le R \le 10^9$, $1 \le a \le 10^9$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
