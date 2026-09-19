We have obtained a satellite photo of land and water conditions, which can be seen as a rectangle consisting of $n$ rows and $m$ columns. Each grid in the rectangle is either land (represented by a period `.` ) or water (represented by a hash `#`).

Although the satellite photo clearly distinguishes between land and water, the specific types of land are not clear. We now understand that for a grid that is water, the land grids reachable within $k$ steps in all four directions (up, down, left, right) will form a beach. For example, the following diagram shows the case for $k=2$, where the blue grids represent water and the yellow grids represent land that forms the beach.

![Example Diagram](https://cdn.luogu.com.cn/upload/image_hosting/bermo74l.png)

Your task is to calculate the number of grids that belong to the "beach" based on the satellite photo. Note: The satellite photo only captures the part that includes water, and **beaches near the water may extend beyond the boundaries of the satellite photo**. You can assume that there is no water outside the satellite photo.

## Input Format

The first line of input contains three integers $n$, $m$, and $k$ separated by spaces, representing the number of rows and columns of the satellite photo, and the range $k$ within which land forms a beach.

The next $n$ lines each contain a string. The length of each string is exactly $m$, representing a row of the satellite photo, where:

- A hash `#` represents a water area;
- A period `.` represents a land area.

## Output Format

Output a single integer on one line, representing the number of beach grids.

## Sample Input and Output

### Sample Input #1

```
2 4 2
##.#
...#
```

### Sample Output #1

```
26
```

### Sample Input #2

```
5 10 3
.........#
..########
.........#
#....###.#
..####...#
```

### Sample Output #2

```
103
```

## Notes/Hints

For $40\%$ of the data, $n=m=1$ holds;  
For $100\%$ of the data, $1 \leq n, m \leq 100$ and $1 \leq k \leq 10$ hold.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
