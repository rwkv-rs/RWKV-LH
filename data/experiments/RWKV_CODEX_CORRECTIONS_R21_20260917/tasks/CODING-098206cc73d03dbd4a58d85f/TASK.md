## Problem Description

Little F loves mathematics, but he always struggles with it in high school.

One day, he was lost in thought during a math class; he reminisced about the past year. A year ago, when he first encountered competitive programming, he felt that the entire world had become new and fresh. How could there be so many wonderful things in this world? Problems that once seemed insurmountable were now easily solved by one algorithm after another.

Little F then realized that there was still so much for him to learn compared to his own immaturity.

A year has passed, and it feels a bit surreal.

He still remembers vividly how one night, listening to the Battle Formation, he was so excited that he couldn't sleep, coding until dawn. Perhaps, this is what passion feels like.

At that time, Little F learned about matrix multiplication. Multiplying two matrices a few times could compute the 10^100th term of the Fibonacci sequence, which was truly marvelous.

However, Little F doesn't want to manually calculate matrix multiplication now—he finds it too tedious. Instead, he has a simple problem. He sketched out an $n \times m$ matrix, where each cell contains a positive integer no greater than $k$.

Little F wants to know how many distinct sub-rectangles in this matrix have a sum that is a multiple of $k$. If a sub-rectangle is described by its top-left and bottom-right corners as $(x_1, y_1, x_2, y_2)$, where $x_1 \le x_2, y_1 \le y_2$; then, two sub-rectangles are considered different if and only if they are represented differently by $(x_1, y_1, x_2, y_2)$. That is, if two rectangles are represented the same by $(x_1, y_1, x_2, y_2)$, they are considered the same rectangle, and you should count them only once in your answer.

## Input Format

Read data from standard input.

The first line of input contains three positive integers $n, m, k$.

The next $n$ lines, each containing $m$ positive integers, represent the matrix, where the $i$-th row and $j$-th column denote the positive integer $a_{i,j}$ in the matrix.

## Output Format

Output to standard output.

Output a single non-negative integer, which is your answer.

## Sample Input and Output

### Input Sample #1

```
2 3 2
1 2 1
2 1 2
```

### Output Sample #1

```
6
```

## Notes

**Sample 1 Explanation**

These rectangles meet the requirement: (1, 1, 1, 3), (1, 1, 2, 2), (1, 2, 1, 2), (1, 2, 2, 3), (2, 1, 2, 1), (2, 3, 2, 3).

Subtasks will provide characteristics of some test data. If you encounter difficulties in solving the problem, you can try to solve only part of the test data.

The scale and characteristics of the data for each test point are as follows:

Special property: All $a_{i,j}$ are the same.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
