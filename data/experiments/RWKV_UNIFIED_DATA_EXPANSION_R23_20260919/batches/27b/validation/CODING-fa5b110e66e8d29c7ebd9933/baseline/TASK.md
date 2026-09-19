Congcong's research has found that the wild people on the island always live in groups, but not all the wild people on the island belong to the same tribe. The wild people always form their own tribes and different tribes often fight with each other. However, all of this remains a mystery—Congcong doesn't even know how the tribes are distributed.

The good news is that Congcong has obtained a map of the island. The map marks the locations of $n$ wild people's dwellings (which can be considered as coordinates on a plane). We know that wild people of the same tribe always live nearby. We define the distance between two tribes as the distance between the two closest dwelling points in the tribes. Congcong has also obtained meaningful information—these wild people are divided into $k$ tribes! This is indeed good news. Congcong hopes to dig out detailed information about all the tribes from this information. He is trying an algorithm that can calculate the distance between two tribes for any method of tribe division, and he hopes to find a method of tribe division that maximizes the distance between the closest two tribes.

For example, the left diagram below represents a good division, while the right one does not. Please program to help Congcong solve this problem.

![Diagram](https://cdn.luogu.com.cn/upload/pic/30573.png)

## Input Format

The first line of the input file contains two integers $n$ and $k$, representing the number of wild people's dwelling points and the number of tribes, respectively.

The next $n$ lines each contain two integers $x$ and $y$, describing the coordinates of a dwelling point.

## Output Format

Output a single line with a real number, which is the distance between the closest two tribes in the optimal division, rounded to two decimal places.

## Sample Input and Output

### Sample Input #1

```
4 2
0 0
0 1
1 1
1 0
```

### Sample Output #1

```
1.00
```

### Sample Input #2

```
9 3
2 2
2 3
3 2
3 3
3 5
3 6
4 6
6 2
6 3
```

### Sample Output #2

```
2.00
```

## Notes

### Data Size and Constraints

For $100\%$ of the data, it is guaranteed that $2 \leq k \leq n \leq 10^3$ and $0 \leq x, y \leq 10^4$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
