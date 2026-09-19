Given a decimal number $x$, convert it to a binary string and pad with leading zeros to make it 16 bits long. This results in a 16-bit binary string, which we use to represent a $4 \times 4$ chessboard, filling it from left to right and top to bottom with $0$ (white pieces) and $1$ (black pieces).

For example, $(447)_{10} = (0000 0001 1011 1111)_2$, filling the board in order (with $0$ as white pieces and $1$ as black pieces), results in the following chessboard (left board):

![](https://cdn.luogu.com.cn/upload/image_hosting/vyma7pie.png)

We can swap adjacent black and white pieces on the chessboard (two squares are adjacent if they share an edge, thus a square can have up to 4 adjacent squares). Transforming the left board to a board where all white pieces are on top and all black pieces are on the bottom (as shown on the right board) requires at least 3 steps.

For a given chessboard (guaranteed to have exactly 8 white pieces and 8 black pieces), find the minimum number of swaps needed to arrange the board with all white pieces on top and all black pieces on the bottom.

## Input Format

Input consists of a single line containing an integer $x$, representing the chessboard in decimal form.

## Output Format

Output a single line containing an integer, the minimum number of swaps required.

## Sample Input and Output

### Sample Input #1

```
447
```

### Sample Output #1

```
3
```

### Sample Input #2

```
42405
```

### Sample Output #2

```
8
```

## Notes

### Sample Explanation
#### Sample 1
Refer to the diagram above, moving the black piece at $(2, 4)$ to $(3, 2)$ requires 3 steps.
#### Sample 2
As shown in the diagram below, $(42405)_{10} = (1010 0101 1010 0101)_2$.

![](https://cdn.luogu.com.cn/upload/image_hosting/aie8kf0n.png)

### Data Size
50% of the test cases guarantee that the board can be arranged with white pieces on top and black pieces on the bottom within 6 swaps.

All data guarantees $0 \leq x < 2^{16}$, and when $x$ is converted to binary, it contains exactly 8 ones.

> This problem originally had a full score of $20\text{pts}$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
