Given a number ladder composed of $n$ rows of numbers as shown in the figure below.

![Number Ladder](https://cdn.luogu.com.cn/upload/pic/12216.png)

The first row of the ladder has $m$ numbers. Starting from the $m$ numbers at the top of the ladder, at each number, one can move either diagonally left or right downwards, forming a path from the top to the bottom of the ladder.

Adhere to the following rules:

1. The $m$ paths from the top to the bottom of the ladder do not intersect at all.
2. The $m$ paths from the top to the bottom of the ladder intersect only at the number nodes.
3. The $m$ paths from the top to the bottom of the ladder are allowed to intersect at number nodes or edges.

## Input Format

The first line contains two positive integers $m$ and $n$, representing the number of digits in the first row and the total number of rows in the number ladder, respectively. The next $n$ lines are the digits in each row of the number ladder.

The first row has $m$ digits, the second row has $m+1$ digits, and so on.

## Output Format

Output the maximum sum of digits calculated according to rule 1, rule 2, and rule 3, each on a new line.

## Sample Input and Output

### Input Sample #1

```
2 5
2 3
3 4 5
9 10 9 1
1 1 10 1 1
1 1 10 12 1 1
```

### Output Sample #1

```
66
75
77
```

## Notes

$1 \leq m, n \leq 20$

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
