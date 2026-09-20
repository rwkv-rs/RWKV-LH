While playing the Somzig game, Little E ran out of time and couldn't hold it together, leading to this problem.

## Problem Description

Little E has balls of \( n \) colors, with \( a_i \) balls of the \( i \)-th color. There are two types of tools: the first type can transform a ball of a specified color into a ball of **any** color; the second type can transform a ball of a specified color into two balls of **the same** color. A transformed ball can also be used with these tools to produce further transformations. There are \( b_i \) tools of the first type and \( c_i \) tools of the second type for the \( i \)-th color. Little E wants to know, if each tool can be used at most once, how many balls of each color \( i \) can he have at most, and how many balls in total can he have at most.

## Input Format

The first line contains a positive integer \( n \).

The second line contains \( n \) integers, where the \( i \)-th integer represents \( a_i \).

The third line contains \( n \) integers, where the \( i \)-th integer represents \( b_i \).

The fourth line contains \( n \) integers, where the \( i \)-th integer represents \( c_i \).

## Output Format

The first line contains \( n \) integers, where the \( i \)-th integer represents the maximum number of balls of the \( i \)-th color Little E can have if each tool is used at most once.

The second line contains one integer, representing the maximum total number of balls Little E can have if each tool is used at most once.

## Sample Input and Output

### Input Sample #1

```
2
1 2
1 2
1 0
```

### Output Sample #1

```
4 3
4
```

## Notes

### Subtasks

It is guaranteed that \( 1 \le n \le 351493 \).

It is guaranteed that \( 0 \le a_i, b_i, c_i \le 10^9 \).

### Usage Agreement

This problem is from the THUPC2024 (2024 Tsinghua University Student Programming Contest and University Invitational) Preliminary.

The term "this repository" refers to the official repository of the THUPC2024 Preliminary ([https://github.com/ckw20/thupc2024_pre_public](https://github.com/ckw20/thupc2024_pre_public)).

1. Any organization or individual may freely use or republish the problems in this repository.

2. Any organization or individual using the problems in this repository should do so without charge and openly. Profiting from these problems or adding special privileges to them is strictly prohibited.

3. If possible, please provide methods to access data, standard solutions, and problem explanations when using these problems; otherwise, please include the GitHub address of this repository.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
