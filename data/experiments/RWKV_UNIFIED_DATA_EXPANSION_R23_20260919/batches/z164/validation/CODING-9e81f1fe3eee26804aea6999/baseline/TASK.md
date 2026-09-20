There was a popular game called Infinity Loop. Let's briefly introduce this game:

The game is played on a grid-shaped board of size $n \times m$, where some small squares contain pipes. The pipes may have interfaces at the midpoints of the boundaries in certain directions. All pipes are of the same thickness, so if the midpoints of the common boundary of two adjacent squares both have interfaces, they can be considered connected. There are 15 types of pipes as shown below:

![](https://cdn.luogu.com.cn/upload/pic/12049.png)

At the start of the game, there may be leaks in the pipes on the board.

Formally, if there exists an interface that is not connected to any other interface, it is a leak.

The player can perform an operation: select a square containing a **non-straight** pipe and rotate the pipe 90 degrees clockwise or counterclockwise around the center of the square.

A straight pipe refers to the two pipes in the middle row of the figure.

Given an initial board state, how many minimum operations are required to ensure there are no leaks on the board?

## Input Format

The first line contains two positive integers $n$ and $m$, representing the size of the grid.

The next $n$ lines each contain $m$ numbers, each of which is an integer between $[0,15]$. You can consider it as a 4-bit binary number, where the bits from low to high represent whether there is a pipe interface at the top, right, bottom, and left directions, respectively, in the initial state.

Specifically, if the number is $0$, it means there is no pipe at that position.

For example, $3(0011_{(2)})$ represents interfaces at the top and right, which is an L-shaped pipe, while $12(1100_{(2)})$ represents interfaces at the bottom and left, which is an L-shaped pipe rotated 180 degrees.

## Output Format

Output a single line, representing the minimum number of operations. If it is impossible to achieve the goal, output $-1$.

## Sample Input and Output

### Sample Input #1

```
2 3
3 14 12
3 11 12
```

### Sample Output #1

```
2
```

### Sample Input #2

```
3 2
1 8
5 10
2 4
```

### Sample Output #2

```
-1
```

### Sample Input #3

```
3 3
9 11 3
13 15 7
12 14 6
```

### Sample Output #3

```
16
```

## Notes

**Sample 1 Explanation**

The board for Sample 1 is as follows:

The rotation method is straightforward: first, rotate the pipe in the dashed square in the top-left corner 90 degrees clockwise.

![](https://cdn.luogu.com.cn/upload/pic/12050.png)

Then, rotate the pipe in the dashed square in the bottom-right corner 90 degrees counterclockwise, thus sealing the pipes.

**Sample 2 Explanation**

Sample 2 corresponds to the first image in the problem description and cannot achieve the goal.

**Sample 3 Explanation**

Sample 3 corresponds to the second image in the problem description. Rotate the pipe in each square except the center square 180 degrees.

![](https://cdn.luogu.com.cn/upload/pic/12051.png)

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
