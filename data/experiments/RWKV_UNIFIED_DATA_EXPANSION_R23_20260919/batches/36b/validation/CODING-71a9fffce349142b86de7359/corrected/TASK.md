Large samples can be downloaded from the "Attachments" at the bottom of the page.

## Problem Description

Little C raises some adorable rabbits. One day, Little C suddenly discovered that the rabbits strictly follow the model proposed by the great mathematician Fibonacci for reproduction: a pair of rabbits, starting from the second month of their birth, will give birth to a pair of baby rabbits at the beginning of each month. We assume that throughout the process, no rabbits will encounter any accidents.

Little C labels the rabbits according to their birth order, starting from 1, and all of Little C's rabbits are descendants of the 1st rabbit. If two pairs of rabbits are born at the same time, Little C will prioritize the pair with the smaller parent label.

If we were to depict this relationship graphically, the first six months would look something like this:

![](https://cdn.luogu.com.cn/upload/pic/9806.png)

In this diagram, an arrow $A \to B$ indicates that $A$ is an ancestor of $B$, and the same color represents rabbits born in the same month.

To better understand how the rabbits reproduce, Little C has gathered some rabbits and posed $m$ questions to you: she wants to know, for each pair of rabbits $a_i$ and $b_i$, who their nearest common ancestor is. Can you help Little C?

The ancestors of a pair of rabbits include the pair themselves and their parents (if any), and the nearest common ancestor is the common ancestor of the two pairs of rabbits that is closest to them in terms of total distance. For example, the nearest common ancestor of 5 and 7 is 2, the nearest common ancestor of 1 and 2 is 1, and the nearest common ancestor of 6 and 6 is 6.

## Input Format

The first line of input contains a positive integer $m$. The next $m$ lines each contain two positive integers, representing $a_i$ and $b_i$.

## Output Format

The output consists of $m$ lines, each containing a positive integer, representing your answer to the questions in order.

## Sample Input and Output

### Input Sample #1

```
5
1 1
2 3
5 7
7 13
4 12
```

### Output Sample #1

```
1
1
2
2
4
```

## Notes

[Data Range and Constraints] Subtasks will provide characteristics of some test data. If you encounter difficulties in solving the problem, you can try to solve only part of the test data. The scale and characteristics of the data for each test point are as follows:

![](https://cdn.luogu.com.cn/upload/pic/9807.png)

Special Property 1: It is guaranteed that $a_i$ and $b_i$ are the pair of rabbits with the largest label born in a certain month. For example, for the first six months, the rabbits with the largest labels are 1, 2, 3, 5, 8, 13.

Special Property 2: It is guaranteed that $|a_i - b_i| \le 1$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
