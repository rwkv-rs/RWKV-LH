Orienteering is a sport that combines intelligence and physical strength. In this activity, participants need to start from the beginning point and reach the designated location in the shortest possible time.

Cow Cow loves this sport very much, but he doesn't know how to reach the finish faster. He heard that you, who are attending the training, are exceptionally intelligent, so he handed you the orienteering map, hoping you could help him solve some problems.

The map Cow Cow gave you describes a flat terrain. The map clearly marks the coordinates of the starting point and the finish point, and also marks several non-intersecting circular areas, each representing a circular water area. For Cow Cow, who cannot swim, entering the water area is impossible. Therefore, Cow Cow's route cannot pass through the water areas. Cow Cow wants to know what the minimum length of such a route can be.

## Input Format

The first line contains four real numbers $S_x, S_y, T_x, T_y$, representing the coordinates of the starting point and the finish point.

The second line contains an integer $n$, representing the number of water areas.

The next $n$ lines, each containing three integers $x_i, y_i, r_i$, represent the coordinates of the center and the radius of a water area.

It is guaranteed that neither the starting point nor the finish point is inside or on the boundary of any water area, and the starting point and the finish point are not the same.

## Output Format

Output a line containing a real number, rounded to exactly one decimal place, representing the answer. Your output must be exactly the same as the standard output to be considered correct.

The test data guarantees that the absolute difference between the rounded answer and the exact answer is no greater than $4 \times 10^{-2}$.

(If you don't know what floating-point error is, you can understand this as: for most algorithms, you can use floating-point numbers normally without special handling.)

## Sample Input and Output

### Sample Input #1

```
2 1 20 11
2
5 5 4
16 9 4
```

### Sample Output #1

```
23.0
```

## Notes

### Sample Explanation

The map is shown below, where the drawn path is the shortest path sought.

![](https://cdn.luogu.com.cn/upload/image_hosting/k4pfy2m5.png)

### Data Range

All data satisfies $0 \leq n \leq 500$, $-1000 \leq x_i, y_i, r_i, S_x, S_y, T_x, T_y \leq 1000$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
