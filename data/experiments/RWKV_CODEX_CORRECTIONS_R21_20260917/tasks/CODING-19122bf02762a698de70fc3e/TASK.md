To enhance her intelligence, ZJY traveled to the New World. However, upon returning, ZJY found that to open the door back to her original world, she must solve a puzzle on the door. The puzzle is as follows:

There is a chessboard with $n$ rows and $m$ columns, on which many special chess pieces can be placed. Each chess piece has an attack range of $3$ rows and $p$ columns. The input data provides a $3 \times p$ matrix that defines the attack range template. The chess piece is assumed to be at the $1$st row and the $k$th column of the template, where positions it can attack are marked as $1$ and positions it cannot attack are marked as $0$. The input guarantees that the $1$st row and $k$th column position is $1$. The password to open the door is the number of ways to place the chess pieces such that no two pieces can attack each other, including the case where no pieces are placed. Since the number of ways can be very large, ZJY only needs to know the result of the number of ways modulo $2^{32}$.

Note: The numbering starts from $0$, meaning the $1$st row refers to the middle row.

## Input Format

The first line of the input contains two integers $n$ and $m$, representing the size of the chessboard.

The second line contains two integers $p$ and $k$, indicating the size of the attack range template and the position of the chess piece within the template.

The next three lines, each containing $p$ numbers, describe the attack range template. Each number is followed by a space.

## Output Format

The output should consist of a single line with one integer, representing the number of feasible arrangements modulo $2^{32}$.

## Sample Input and Output

### Input Sample #1

```
5 5
3 1
0 1 0
1 1 1
0 1 0
```

### Output Sample #1

```
55447
```

## Notes

### Data Range

For $10\%$ of the data, $1 \leq n \leq 5$, $1 \leq m \leq 5$.

For $50\%$ of the data, $1 \leq n \leq 1000$, $1 \leq m \leq 6$.

For $100\%$ of the data, $1 \leq n \leq 10^{6}$, $1 \leq m \leq 6$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
