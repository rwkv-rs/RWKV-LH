You are given a grid of size \( r \times c \) with some boxes placed on it. We can obtain its three views (as shown in the figure, the left matrix represents the number of boxes placed on each position, and the right three views are the front view, top view, and left view):

![](https://onlinejudgeimages.s3-ap-northeast-1.amazonaws.com/problem/14635/1.png)

You can remove some boxes and rearrange the remaining boxes. You want to know the maximum number of boxes you can remove such that the front view, top view, and left view remain unchanged after rearrangement.

For example, in the given example, it is possible to remove 9 boxes and rearrange them as follows:

![](https://onlinejudgeimages.s3-ap-northeast-1.amazonaws.com/problem/14635/2.png)

Given \( 1 \le r, c \le 100 \), the number of boxes at each position is in the range \([0, 10^9]\).

## Input Format

The first line of input contains two integers \( r \) and \( c \) (\( 1 \le r, c \le 100 \)), representing the number of rows and columns in the grid, respectively. Each of the following \( r \) lines contains \( c \) integers, representing the heights (in boxes) of the piles in the corresponding row. All heights are between 0 and \( 10^9 \) inclusive.

## Output Format

Display the maximum number of boxes that can be removed without being detected.

## Sample Input and Output

### Input Sample #1

```
5 5
1 4 0 5 2
2 1 2 0 1
0 2 3 4 4
0 3 0 3 1
1 2 2 1 1
```

### Output Sample #1

```
9
```

### Input Sample #2

```
2 3
50 20 3
20 10 3
```

### Output Sample #2

```
30
```

## Notes/Hints

Time limit: 1 second, Memory limit: 512 MB.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
