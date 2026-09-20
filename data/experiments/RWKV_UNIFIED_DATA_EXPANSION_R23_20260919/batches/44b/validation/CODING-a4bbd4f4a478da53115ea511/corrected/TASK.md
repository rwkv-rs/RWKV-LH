There are $n$ lights arranged in a row, numbered from left to right as $1, 2, \ldots, n$. Then, $m$ operations are performed sequentially.

The operations are of two types:

1. Specify an interval $[a, b]$ and toggle the state of the lights within this interval (turn on the off lights and turn off the on lights).
2. Specify an interval $[a, b]$ and output the number of lights that are on within this interval.

**All lights are initially off.**

## Input Format

The first line contains two integers $n$ and $m$, representing the number of lights and the number of operations, respectively.

The next $m$ lines each contain three integers: $c, a, b$. Here, $c$ denotes the type of operation.

- When $c$ is $0$, it indicates the first type of operation.
- When $c$ is $1$, it indicates the second type of operation.

$a$ and $b$ represent the left and right boundaries of the operation interval, respectively.

## Output Format

Whenever the second type of operation is encountered, output a line containing a single integer, which represents the number of lights that are on in the queried interval.

## Sample Input and Output

### Input Sample #1

```
4 5
0 1 2
0 2 4
1 2 3
0 2 4
1 1 4
```

### Output Sample #1

```
1
2
```

## Notes/Hints

### Data Size and Constraints

For all test cases, it is guaranteed that $2 \le n \le 10^5$, $1 \le m \le 10^5$, $1 \le a, b \le n$, and $c \in \{0, 1\}$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
