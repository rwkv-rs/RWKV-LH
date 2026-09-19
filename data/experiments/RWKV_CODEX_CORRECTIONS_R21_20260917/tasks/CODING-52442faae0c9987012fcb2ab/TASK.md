Amaya Koyomi gives you a sequence of length $n$. Define a subinterval of interval $[l, r]$ as all intervals of the form $[l', r']$, where $l', r'$ are integers and $l \le l' \le r' \le r$.

There are $m$ operations:

`1 x y`: Modify the value at position $x$ to $y$.

`2 l r x`: Query how many subintervals in interval $[l, r]$ have a maximum value less than or equal to $x$.

## Input Format

The first line contains two integers $n$ and $m$. The second line contains $n$ integers representing the sequence.

The next $m$ lines, each in the form of `1 x y` or `2 l r x`, describe the operations.

## Output Format

For each operation of type `2`, output a single line with the answer.

## Sample Input and Output

### Input Sample #1

```
6 6
1 1 4 5 1 4
1 1 4
2 1 4 2
2 1 1 4
2 1 5 4
1 5 4 
2 3 3 3
```

### Output Sample #1

```
1
1
7
0
```

## Notes/Hints

For $100\%$ of the data, $n, m \le 3 \times 10^5$, $1 \le l \le r \le n$, $1 \le x, y \le n$, each element in the sequence is within $[1, n]$, and all numbers are integers.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
