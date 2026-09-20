Consider a 4-hypercube, also known as a tesseract. A unit solid tesseract is a 4D figure that is the convex hull of 16 points with Cartesian coordinates $(±½, ±½, ±½, ±½)$ -- its vertices. It has 32 edges (1D), 24 square faces (2D), and 8 cubic 3-faces (3D) also known as cells. We study hollow tesseracts and define a tesseract as the boundary of a solid tesseract. Thus, a tesseract is a connected union of 8 solid cubes (its cells) that intersect each other at 24 tesseract's square faces, 32 edges, and 16 vertices.

Let's cut a tesseract along 17 of its 24 faces, so that it remains connected via 7 faces that were left intact. Unfold the tesseract into a 3D hyperplane by rotating its constituting cubes along the faces that were left intact until all its cells lie in the same 3D hyperplane. The result is called a 3-net of a tesseract. This process is a natural generalization of how a 3D cube is cut and unfolded onto a 2D plane to produce a 2-net of a cube that consists of 6 squares.

In this problem, you are given a tree-like 8-polycube in 3D space, also known as an octocube. An octocube is a collection of 8 unit cubical cells joined face-to-face. More formally, the intersection of each pair of cubical cells constituting an octocube is either empty, a point, a unit line (1D), or a unit square (2D). The given octocube is tree-like in the following sense. Consider the adjacency graph of the octocube -- a graph with 8 vertices corresponding to its 8 cells. There is an edge in the adjacency graph between pairs of adjacent cells. Two cells of an octocube are called adjacent when their intersection is a square. Cells that intersect at a point or a line are not considered adjacent. An octocube is called tree-like when its adjacency graph is a tree.

Your task is to determine whether the given tree-like octocube constitutes a 3-net of a tesseract. That is, whether this octocube, when placed onto a hyperplane in 4D space, can be folded in 4D space along the squares of intersection between its cells into a tesseract.

## Input Format

The first line of the input file contains three integers $m, n, k$ -- the width, the depth, and the height of the box that contains the given octocube $(1 \le m, n, k \le 8)$. The following $k$ groups of lines describe rectangular slices of the box from top to bottom. Each slice is described by $n$ rows with $m$ characters each. The characters on a line are either `.` denoting an empty space, or `x` denoting a unit cube. The input file is guaranteed to describe a tree-like octocube.

## Output Format

Write to the output file a single word `Yes` if the given octocube can be folded into a tesseract or `No` otherwise.

## Sample Input and Output

### Input Sample #1

```
3 3 4
...
.x.
...
.x.
xxx
.x.
...
.x.
...
...
.x.
...
```

### Output Sample #1

```
Yes
```

### Input Sample #2

```
8 1 1
xxxxxxxx
```

### Output Sample #2

```
No
```

## Notes/Hints

Time limit: 1 s, Memory limit: 256 MB.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
