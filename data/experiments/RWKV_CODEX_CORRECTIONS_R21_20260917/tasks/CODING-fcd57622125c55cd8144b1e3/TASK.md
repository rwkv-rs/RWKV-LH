Given a string of digits of length $n$, where each digit is between $0$ and $9$ inclusive, indexed from $1$.

Perform $m$ range queries. Each query looks for the sum of the digits in the range $[A, B]$, and after each query, increment each digit in the range by $1$. Specifically, if a digit is $9$ before incrementing, it becomes $0$ after incrementing.

Output the sum of the digits for each query.

## Input Format

The first line contains two integers $n$ and $m$.

The second line contains $n$ digit characters without spaces.

The next $m$ lines each contain two integers $A$ and $B$, representing the range $[A, B]$ for the query.

## Output Format

Output $m$ lines, each containing the sum of the digits for the corresponding query.

## Sample Input and Output

### Sample Input #1

```
4 3
1234
1 4
1 4
1 4
```

### Sample Output #1

```
10
14
18
```

### Sample Input #2

```
4 4
1234
1 1
1 2
1 3
1 4
```

### Sample Output #2

```
1
4
9
16
```

### Sample Input #3

```
7 5
9081337
1 3
3 7
1 3
3 7
1 3
```

### Sample Output #3

```
17
23
1
19
5
```

## Notes

### Data Size and Constraints

For $100\%$ of the data, it is guaranteed that $1 \le n \le 2.5 \times 10^5$, $1 \le m \le 10^5$, and $1 \le A, B \le n$.

### Notes

**This problem is translated from [COCI2007-2008](https://hsin.hr/coci/archive/2007_2008/) [CONTEST #3](https://hsin.hr/coci/archive/2007_2008/contest3_tasks.pdf) *T6 REDOKS***.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
