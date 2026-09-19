Given a matrix of size $n \times m$ consisting only of `.` and `*`.

The `*` in the matrix form several non-overlapping rectangles. They do not touch at edges or vertices.

Determine the number of rectangles.

## Input Format

The first line contains two positive integers $n$ and $m$.

The following $n$ lines represent the matrix described in the problem. The matrix consists only of `.` and `*`.

## Output Format

Output a single non-negative integer, which is your answer.

## Sample Input and Output

### Sample Input #1

```
6 7
***....
***..**
.....**
.***.**
.***...
.***...
```

### Sample Output #1

```
3
```

### Sample Input #2

```
3 3
*.*
...
*.*
```

### Sample Output #2

```
4
```

### Sample Input #3

```
1 10
.*.**.***.
```

### Sample Output #3

```
3
```

## Notes

### Data Range

- For $10$ points, each rectangle in the matrix contains only one `*`.
- For another $15$ points, it is guaranteed that $n = 1$.
- For all data, $1 \leq n, m \leq 100$.

### Notes

**The problem is translated from [COCI2019-2020](https://hsin.hr/coci/archive/2019_2020/) [CONTEST #5](https://hsin.hr/coci/archive/2019_2020/contest5_tasks.pdf) _T1 Emacs_**, translated by [90693](/user/90693).

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
