The Dome of Circus
A traveling circus faces a significant challenge in designing a dome for their performances. Many circus acts take place in the air under the dome above the stage. Various rigs, supports, and anchors need to be installed above the stage but below the dome.

The dome itself must be above the center of the stage and should be conical in shape. The space under the dome must be air-conditioned, so our goal is to design the dome with the smallest possible volume.

There are n points in space; $(x_i, y_i, z_i)  1≤i≤n$ are the coordinates of the points that must be covered by the dome above the stage.

The ground is represented by the plane $z = 0$, with the $z$ coordinate pointing upwards. The center of the stage is at the ground point $(0,0,0)$.

The tip of the dome must be at a point with coordinates $(0,0,h)$ where $h>0$.

The dome must be conical, with its base touching the ground at the point $(0,0,0)$ and having a radius of $r$. The dome must contain or touch all of the $n$ given points.

With these constraints in mind, the volume of the dome must be minimized.

![](https://cdn.luogu.com.cn/upload/image_hosting/vodwuwe0.png)

## Input

The input file contains several test cases, each described below. The first line of the input file contains an integer $n(1≤n≤10000)$ — the number of points under the dome.

The next $n$ lines describe one point per line with three floating-point numbers $x_i, y_i$, and $z_i$ — the coordinates of the $i^{th}$ point. The absolute values of all coordinates do not exceed $1000$, with up to 2 decimal places. All $z_i$ values are positive. There is at least one point where $x_i$ or $y_i$ is non-zero.

## Output

For each test case, write a single line containing two floating-point numbers $h$ and $r$, which are the height and base radius of the dome. These numbers must be accurate to 3 decimal places.
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
