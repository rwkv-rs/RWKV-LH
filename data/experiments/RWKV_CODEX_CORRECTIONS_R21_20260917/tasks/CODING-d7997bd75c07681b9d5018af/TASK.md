A complete set of dominoes consists of 28 tiles, each of which can be flipped (for example, 0 1 can be flipped to 1 0):

![](https://cdn.luogu.org/upload/pic/46306.png)

In this context, "Bone" represents the domino's identifier, and "Pips" represents the two numbers on the domino.

Given a 7x8 matrix, the task is to output a placement scheme where each cell in the scheme matrix (also 7x8) contains a domino identifier. This identifier should allow for replacing the original matrix with the domino corresponding to that identifier. Output both the placement scheme and the total number of such schemes.

(For example, 0 5 can be transformed into 6 6, 4 3 can be transformed into 20 20, and similarly, 20 20 in the scheme can be replaced back to 4 3 or 3 4 according to the table above.)

For example, consider the following matrix:

![](https://cdn.luogu.org/upload/pic/46310.png)

It can be converted using the table above into:

![](https://cdn.luogu.org/upload/pic/46309.png)

Note: The boxes are manually added, and the boxed area represents a complete domino to help understand the problem.

## Input and Output Example

### Input Example #1

```
5 4 3 6 5 3 4 6
0 6 0 1 2 3 1 1
3 2 6 5 0 4 2 0
5 3 6 2 3 2 0 6
4 0 4 1 0 0 4 1
5 2 2 4 4 1 6 5
5 5 3 6 1 2 3 1
4 2 5 2 6 3 5 4
5 0 4 3 1 4 1 1
1 2 3 0 2 2 2 2
1 4 0 1 3 5 6 5
4 0 6 0 3 6 6 5
4 0 1 6 4 0 3 0
6 5 3 6 2 1 5 3
```

### Output Example #1

```
Layout #1:
5 4 3 6 5 3 4 6
0 6 0 1 2 3 1 1
3 2 6 5 0 4 2 0
5 3 6 2 3 2 0 6
4 0 4 1 0 0 4 1
5 2 2 4 4 1 6 5
5 5 3 6 1 2 3 1
Maps resulting from layout #1 are:
6 20 20 27 27 19 25 25
6 18 2 2 3 19 8 8
21 18 28 17 3 16 16 7
21 4 28 17 15 15 5 7
24 4 11 11 1 1 5 12
24 14 14 23 23 13 13 12
26 26 22 22 9 9 10 10
There are 1 solution(s) for layout #1.
Layout #2:
4 2 5 2 6 3 5 4
5 0 4 3 1 4 1 1
1 2 3 0 2 2 2 2
1 4 0 1 3 5 6 5
4 0 6 0 3 6 6 5
4 0 1 6 4 0 3 0
6 5 3 6 2 1 5 3
Maps resulting from layout #2 are:
16 16 24 18 18 20 12 11
6 6 24 10 10 20 12 11
8 15 15 3 3 17 14 14
8 5 5 2 19 17 28 26
23 1 13 2 19 7 28 26
23 1 13 25 25 7 4 4
27 27 22 22 9 9 21 21
16 16 24 18 18 20 12 11
6 6 24 10 10 20 12 11
8 15 15 3 3 17 14 14
8 5 5 2 19 17 28 26
23 1 13 2 19 7 28 26
23 1 13 25 25 7 21 4
27 27 22 22 9 9 21 4
There are 2 solution(s) for layout #2.
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
