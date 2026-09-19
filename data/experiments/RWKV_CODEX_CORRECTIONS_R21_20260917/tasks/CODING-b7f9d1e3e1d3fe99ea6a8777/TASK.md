ustze loves geometry and believes it is the simplest part of competitive mathematics. After mastering mathematics, he decided to apply his talents to computational geometry and challenge traditional Euclidean geometry.

As a defender of Euclidean geometry, Tinytree established a **spherical surface with its center at the origin and radius** $\boldsymbol{R}$ in a three-dimensional space. The point with coordinates $(0,0,R)$ is called the North Pole, which is obviously on the spherical surface. In Euclidean geometry, three points uniquely determine a circle in space. Therefore, Tinytree identified $N$ pairs of points on the spherical surface, where each pair along with the North Pole determines a circle on the spherical surface. We guarantee that the **radius of these circles is strictly less than** $\boldsymbol{R}$. Thus, each circle divides the spherical surface into two parts of unequal areas. We **define the smaller area as the interior of the circle and the larger area as the exterior**. The interiors of these $N$ circles, protected by Tinytree, **form the safe region**.

As an enthusiast of non-Euclidean geometry, ustze considers circles on the spherical surface as "straight lines". He identified $M$ pairs of points on the spherical surface, where each pair along with the North Pole also determines a circle on the spherical surface. The **radius of these circles is also strictly less than** $\boldsymbol{R}$. The interiors of these $M$ circles, under the threat of ustze, **form the danger region**.

While Tinytree and ustze are in confrontation, Kiana, an ordinary passerby on the spherical surface, is terrified by the scene and starts to hide and dodge. Kiana has initially identified $T$ points on the spherical surface and wants to know if these points are in the safe or danger region to plan her escape. Since Kiana cannot calculate this herself, she hopes you can help her.

## Input Format

The first line contains three positive integers $N, M$, and $T$ ($1 \le N, M \le 5000$, $1 \le T \le 1.5 \times 10^5$), representing the number of point pairs identified by Tinytree, the number of point pairs identified by ustze, and the number of escape points identified by Kiana, respectively.

The second line contains a positive integer $R$ ($1 \le R \le 10^3$), representing the radius of the spherical surface.

The next $N$ lines, the $i$-th line contains $A_i, B_i, X_i, C_i, D_i, Y_i$ ($1 \le |A_i|, |B_i|, |C_i|, |D_i| \le R$, $1 \le A_i^2 + B_i^2, C_i^2 + D_i^2 \le R^2$), where $A_i, B_i$ represent the horizontal and vertical coordinates of the first point in the $i$-th pair identified by Tinytree, and $X_i$ indicates the sign of the vertical coordinate of the first point (`+` for positive, `-` for negative, randomly chosen between `+` and `-` if zero). $C_i, D_i$ represent the horizontal and vertical coordinates of the second point in the $i$-th pair identified by Tinytree, and $Y_i$ indicates the sign of the vertical coordinate, with the same meaning as $X_i$.

The next $M$ lines, the $j$-th line contains $A_j, B_j, X_j, C_j, D_j, Y_j$ ($1 \le |A_j|, |B_j|, |C_j|, |D_j| \le R$, $1 \le A_j^2 + B_j^2, C_j^2 + D_j^2 \le R^2$), representing the coordinates of the $j$-th pair identified by ustze, with the same point representation as before.

The next $T$ lines, the $k$-th line contains two real numbers $A_k, B_k$ ($1 \le |A_k|, |B_k| \le R$, $1 \le A_k^2 + B_k^2 \le R^2$) and a character $X_k$, representing the $k$-th escape point identified by Kiana, with the same point representation as before.

The data guarantees validity, and no two points in the input are the same. All real numbers are rounded to three decimal places. The **minimum straight-line distance between Kiana's escape points and any given circle is not less than** $\boldsymbol{10^{-6}}$.

## Output Format

The output consists of $T$ lines, each containing a string. If Kiana's $k$-th escape point is in the safe region, output `Safe` on the $k$-th line. If it is not in the safe region but also not in the danger region, output `Passer` on the $k$-th line. If it is not in the safe region and is in the danger region, output `Goodbye` on the $k$-th line (all outputs are without quotes).

## Sample Input and Output

### Input Sample #1

```
2 2 4
3
2.571 0.514 + 2.571 -0.514 +
-2.571 0.514 + -2.571 -0.514 +
0.514 2.571 + -0.514 2.571 +
0.514 -2.571 + -0.514 -2.571 +
2.118 -2.118 -
1.051 1.051 +
-0.468 1.870 +
-1.870 -0.468 +
```

### Output Sample #1

```
Passer
Safe
Goodbye
Safe
```

## Notes/Hints

In a three-dimensional space, we can describe the position of a point using an ordered triple of real numbers $(x, y, z)$, where $x, y, z$ are respectively called the horizontal, vertical, and vertical coordinates of the point.

A spherical surface with its center at $(x_0, y_0, z_0)$ and radius $R$ refers to the set of all points $(x, y, z)$ in space that satisfy $(x - x_0)^2 + (y - y_0)^2 + (z - z_0)^2 = R^2$. For two given distinct points $(x_1, y_1, z_1)$ and $(x_2, y_2, z_2)$ on this spherical surface, if they are not antipodal points (two points are antipodal if and only if the distance between them is $2R$), then they and the center are not collinear. These three points uniquely determine a plane, and the intersection of this plane with the spherical surface is divided by these two points into two parts, with the shorter part's length being defined as the distance between these two points on the spherical surface. If the two points are antipodal, their distance is defined as $\pi R$. A circle on the spherical surface refers to the set of points on the spherical surface whose spherical distance to a given point is a constant. It can be proven that any three distinct points on the spherical surface uniquely determine a circle on the spherical surface.

**[Problem Source]**

This problem is from the 2021 Tsinghua University Student Programming Contest and University Invitational Tournament (THUPC2021) Preliminary Round.

Solutions and other resources can be found at <https://github.com/THUSAAC/THUPC2021-pre>.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
