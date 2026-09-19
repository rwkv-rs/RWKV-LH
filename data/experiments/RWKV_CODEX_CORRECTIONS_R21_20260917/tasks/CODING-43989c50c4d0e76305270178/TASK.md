Given an $\operatorname{H}\times\operatorname{W}$ rectangular grid, Xiao Ming wants to draw a pair of touching circles within this grid with no overlapping areas, and each circle having a radius that is a positive integer. Since Xiao Ming dislikes precision errors, the center of each circle must be located at the intersection points of the grid. You need to help Xiao Ming determine the number of ways he can do this. 

## Input Format
The first line contains a positive integer $\operatorname{T}$, representing the number of test cases. The following $\operatorname{T}$ lines each contain two positive integers, $\operatorname{W}$ and $\operatorname{H}$, representing the grid size.

## Output Format
Output consists of $\operatorname{T}$ lines, each line corresponding to a test case result. The output format for the $i^{th}$ case should be `Case i: result`. The result is guaranteed to be at most $2^{64}-1$.

## Sample Input

```
5
4 2
4 3
4 4
4 6
10 10
```

## Sample Output

```
Case 1: 1
Case 2: 2
Case 3: 6
Case 4: 16
Case 5: 496
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
