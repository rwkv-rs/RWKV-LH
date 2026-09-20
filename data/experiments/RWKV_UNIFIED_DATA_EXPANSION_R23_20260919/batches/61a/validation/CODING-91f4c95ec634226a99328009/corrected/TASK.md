There is a chessboard with \( n \) rows and \( m \) columns. A horse wants to jump from the top-left corner to the bottom-right corner of the board. Each step, the horse jumps to the right by an odd number of columns and lands on the same row or an adjacent row. The horse must not leave the chessboard during the jumps. For example, when \( n = 3 \) and \( m = 10 \), the following diagram shows a feasible jumping method.

![](https://cdn.luogu.com.cn/upload/pic/9367.png)

Calculate the number of jumping methods modulo \( 30,011 \).

## Input Format

A single line containing two positive integers \( n \) and \( m \), representing the dimensions of the chessboard.

## Output Format

A single line containing an integer, which is the number of jumping methods modulo \( 30,011 \).

## Sample Input and Output

### Sample Input #1

```
3 5
```

### Sample Output #1

```
10
```

## Notes

- For \( 10\% \) of the data, \( 1 \leq n \leq 10 \) and \( 2 \leq m \leq 10 \);
- For \( 50\% \) of the data, \( 1 \leq n \leq 10 \) and \( 2 \leq m \leq 10^5 \);
- For \( 80\% \) of the data, \( 1 \leq n \leq 10 \) and \( 2 \leq m \leq 10^9 \);
- For \( 100\% \) of the data, \( 1 \leq n \leq 50 \) and \( 2 \leq m \leq 10^9 \).

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
