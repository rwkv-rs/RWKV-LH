Suppose you have a wooden board of length $5$, initially uncolored. You wish to paint its $5$ units of length in red, green, blue, green, and red, respectively, represented by a string of length $5$: $\texttt{RGBGR}$.

Each time, you can paint a continuous segment of the board with a given color, with subsequent colors overwriting previous ones. For example, first paint the board as $\texttt{RRRRR}$, then as $\texttt{RGGGR}$, and finally as $\texttt{RGBGR}$, achieving the target.

Use the fewest number of painting operations to reach the target.

## Input Format

The input consists of a single line containing a string of length $n$, which is the target coloring. Each character in the string is an uppercase letter, where different letters represent different colors, and the same letters represent the same color.

## Output Format

The output consists of a single number, which is the minimum number of painting operations required.

## Sample Input and Output

### Sample Input #1

```
AAAAA
```

### Sample Output #1

```
1
```

### Sample Input #2

```
RGBGR
```

### Sample Output #2

```
3
```

## Notes

$40\%$ of the test cases satisfy $1 \le n \le 10$.

$100\%$ of the test cases satisfy $1 \le n \le 50$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
