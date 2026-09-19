You're given a sequence A of N non-negative integers. Answer Q queries, where each query consists of three integers: v, a, b. The answer is number of pairs of integers i and j that satisfy these conditions:

1 <= i <= j <= N

a <= j-i+1 <= b

A\[k\] >= v for every integer k between i and j, inclusive

## Input Format

The first line of input contains two integers, N and Q. The second line contains the sequence A, consisting of N integers. Each of the next Q lines contains three numbers, v, a and b, defining a query.

## Output Format

In the i-th line output only one integer denoting the answer to the i-th query.

## Sample Input and Output

### Sample Input #1

```
5 3
5 3 2 7 4
3 2 3
2 2 5
4 1 1
```

### Sample Output #1

```
2
10
3
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
