There is a sequence of $N$ integers $X_1, X_2, \cdots, X_N$ followed by $K$ operations which can be:

+ Modify a particular element in $X$ to another number;
+ Given $i, j$, determine the sign of $\prod_{k=i}^{j} X_k$ (i.e., positive, negative, or $0$).

## Input Format

Multiple datasets.

The first line of each dataset contains two positive integers $N$ and $K$.

The second line contains $N$ integers $X_1, X_2, \cdots, X_N$.

The following $K$ lines start with a letter; if it is `C`, it is followed by two integers $I, V`, indicating that $X_I$ needs to be updated to $V`; if it is `P`, it is followed by two positive integers $I, J`, asking for the sign of $\prod_{k=I}^{J} X_k$.

## Output Format

For each dataset, print a single line where the $i$-th character corresponds to the result of the $i$-th `P` operation (output `+` if positive, `-` if negative, and `0` if zero).

## Sample Input

### Sample Input #1

```
4 6
-2 6 0 -1
C 1 10
P 1 4
C 3 7
P 2 2
C 4 -5
P 1 4
5 9
1 5 -2 4 3
P 1 2
P 1 5
C 4 -5
P 1 5
P 4 5
C 3 0
P 1 5
C 4 -5
C 4 -5
```

## Sample Output

```
0+-
+-+-0
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
