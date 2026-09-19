Windy has $N$ wooden planks that need to be painted. Each plank is divided into $M$ squares. Each square needs to be painted either red or blue.

Windy can only paint a continuous segment of squares on one plank with one color at a time. Each square can be painted at most once.

If Windy can only paint $T$ times, what is the maximum number of squares he can paint correctly?

A square is considered incorrectly painted if it is either not painted or painted with the wrong color.

## Input Format

The first line contains three integers, $N, M, T$.

The next $N$ lines each contain a string of length $M$, where `0` represents red and `1` represents blue.

## Output Format

Output a single integer, the maximum number of correctly painted squares.

## Sample Input and Output

### Sample Input #1

```
3 6 3
111111
000000
001100
```

### Sample Output #1

```
16
```

## Notes/Hints

$30\%$ of the test cases satisfy $1 \le N, M \le 10, 0 \le T \le 100$.

$100\%$ of the test cases satisfy $1 \le N, M \le 50, 0 \le T \le 2500$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
