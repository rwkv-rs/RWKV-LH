> Stars cling to the clouds, splashing, dew drips from the jade liquid, the precious steps of sorrow are neatly cut. The blue sky is like a silk ribbon, the light shakes the Northern Dipper.
>
> —— [Yuan] Meng Fang, "Tian Jing Sha · Xing Yi Yun Zhu Jian Jian"

Little P strolls under the starry sky.

"I'll pluck a star for you, and you are my whole world."

"Tonight, I don't care about humanity, I only think of you."

## Problem Description

Consider the starry sky as a Cartesian coordinate system, with Little P's position at the origin $(0,0)$. There are $n$ stars in the sky, with the $i$-th star located at $(x_i, y_i)$.

Little P initially faces the point $(1,0)$, and then he will perform $m$ rotations in place. After the $i$-th rotation, he will face the point $(u_i, v_i)$.

He can choose to rotate either counterclockwise or clockwise. The rotation stops immediately when he faces the direction he is meant to face.

He believes that the more stars he sees directly in front of him during the rotation, the better.

Little P wants to know the maximum number of stars he can have directly in front of him during each rotation (including the stars visible at the initial and final directions).

## Input Format

The input consists of $n+m+1$ lines.

The first line contains two positive integers $n$ and $m$, representing the number of stars and the number of rotations, respectively.

The next $n$ lines each contain two integers $x_i$ and $y_i$.

The next $m$ lines each contain two integers $u_i$ and $v_i$, as described in the problem statement.

Each pair of numbers on a line is separated by a single space. The data is in Linux format, with no extra spaces at the end of the lines.

## Output Format

The output consists of $m$ lines, each containing a single integer. The $i$-th line represents the answer for the $i$-th rotation.

## Sample Input and Output

### Sample Input #1

```
5 2
1 0
1 1
2 2
-1 2
-2 -1
-1 1
-1 2
```

### Sample Output #1

```
4
5
```

### Sample Input #2

```
See the provided file ex_star2.in
```

### Sample Output #2

```
See the provided file ex_star2.out
```

### Sample Input #3

```
See the provided file ex_star3.in
```

### Sample Output #3

```
See the provided file ex_star3.out
```

## Notes

The diagram for Sample 1 is as follows:

![Diagram for Sample 1](https://cdn.luogu.com.cn/upload/image_hosting/h2t5eu1a.png)

The orange dots represent stars, and the green dot represents Little P's first rotation position. For the first rotation, from $(1,0)$ to $(-1,1)$, if rotating clockwise (blue area, including boundaries), there are $2$ stars; if rotating counterclockwise (green area, including boundaries), there are $4$ stars.

For the second rotation, from $(-1,1)$ to $(-1,2)$, all $5$ stars will be in front of Little P during the counterclockwise rotation.

![Diagram for Sample 1](https://cdn.luogu.com.cn/upload/image_hosting/b22go7at.png)

Except for test points $24$ and $25$, all other test points guarantee that the absolute values of all coordinates are $\leq 1000$.

For the first $12$ test points, it is guaranteed that no other stars lie on the line formed from the origin to any star.

Except for test points $23$ and $25$, for all odd-numbered test points, it is guaranteed that there are no stars in the initial and target directions of each rotation.

Except for test points $22$ and $24$, for all even-numbered test points, it is guaranteed that there is at least one star in the initial and target directions of each rotation.

For $100\%$ of the data, it is guaranteed that the coordinates of the stars are unique, that no coordinate is $(0,0)$, and that the initial direction of rotation is never equal to the final direction.

Sample $3$ meets the constraints for even-numbered test points.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
