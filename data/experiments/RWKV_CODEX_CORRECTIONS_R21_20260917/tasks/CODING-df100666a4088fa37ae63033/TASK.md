Garik and Andrey work in the adjustment office and are trying to predict the future. They are given a large $n \times n$ square matrix. Initially, each element $(x, y)$ in the matrix is filled with the value $x + y$ (where $1 \le x, y \le n$).

There are two types of queries to predict the future:

- `R r` — Print the sum of all values in row $r$ and then set all values in row $r$ to $0$.
- `C c` — Print the sum of all values in column $c$ and then set all values in column $c$ to $0$.

Write a program to process these queries.

## Input Format

The first line contains two integers, $n$ and $q$, representing the size of the matrix and the number of queries, respectively ($1 \le n \le 10^6$, $1 \le q \le 10^5$).

The next $q$ lines each contain a query of the form `R r` (where $1 \le r \le n$) or `C c` (where $1 \le c \le n$).

## Output Format

Output $q$ lines, each containing the result of the corresponding query.

## Sample Input and Output

### Input Sample #1

```
3 7
R 2
C 3
R 2
R 1
C 2
C 1
R 3
```

### Output Sample #1

```
12
10
0
5
5
4
0
```

## Notes

Time limit: 1 second, Memory limit: 256 MB.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
