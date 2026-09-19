This is an ordinary die. It is a homogeneous convex polyhedron with n vertices and f faces, each of which is a convex polygon, and no two faces are coplanar. When this die is thrown into the air, it does not bounce again upon landing (this is an extremely ideal scenario).

You want to know the probability of each face landing on the ground. The probability of each face landing on the ground can be calculated as follows: We assume O to be the center of gravity of the die, and with O as the center, we create a unit sphere S with a radius of 1.

We know that the surface area of S, which is a unit sphere, is 4*pi, where pi is the mathematical constant representing the ratio of a circle's circumference to its diameter. For a given face C of the die, there exists a region T on the sphere S such that if the point of intersection between the gravitational direction of the die and S falls within T, then C is the face that lands on the ground. The probability of C landing on the ground is the area of region T divided by 4*pi.

To better assist in calculating the area of a region on the sphere, we provide the formula for calculating the area of a triangle on the unit sphere S. Consider three great circles on the unit sphere S that intersect pairwise at points A, B, and C. The area of the spherical triangle ABC is given by $\text{Area}(ABC) = \alpha + \beta + \gamma - \pi$, where $\alpha, \beta, \gamma$ are the sizes of the three dihedral angles. See the figure below for reference.

![Figure](https://cdn.luogu.com.cn/upload/pic/12756.png)

We guarantee that when each face lands on the ground, the orthocenter of the center of gravity is exactly within that face. This means there will be no unstable situations.

## Input Format

The first line contains two integers, representing the total number of vertices n and the total number of faces f, both numbered starting from 1.

The next n lines each contain three floating-point numbers x, y, and z, giving the coordinates of each vertex.

The next f lines describe each face in turn. First, an integer d, not less than 3, indicates the number of vertices on this face, followed by d integers giving the vertex numbers in counterclockwise order (viewed from outside the die).

## Output Format

Output f lines, where the i-th line contains a floating-point number representing the probability of the i-th face landing on the ground. Your output should be rounded to the nearest 7 decimal places, ensuring that it is closest to the standard answer under the condition of retaining 7 decimal places. The data guarantees to avoid precision errors caused by rounding to the eighth decimal place.

## Sample Input and Output

### Input Sample #1

```
8 6
1 0 0
1 1 0
1 0 1
1 1 1
0 0 0
0 1 0
0 0 1
0 1 1
4 1 2 4 3
4 2 6 8 4
4 6 5 7 8
4 5 1 3 7
4 3 4 8 7
4 1 5 6 2
```

### Output Sample #1

```
0.1666667
0.1666667
0.1666667
0.1666667
0.1666667
0.1666667
```

## Notes

For all data, 4 <= n <= 50 and 4 <= f <= 50, and the absolute values of all coordinates are within 10000.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
