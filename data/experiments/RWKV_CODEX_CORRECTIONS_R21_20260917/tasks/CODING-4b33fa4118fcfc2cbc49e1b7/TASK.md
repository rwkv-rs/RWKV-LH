Bessie is a bionic cow. On a number line, she is trying to hit $T$ ($1 \leq T \leq 10^5$) targets located at different positions. Bessie starts at position $0$ and follows a sequence of $C$ ($1 \leq C \leq 10^5$) commands consisting of `L`, `F`, and `R`:

- `L`: Bessie moves one unit to the left.
- `R`: Bessie moves one unit to the right.
- `F`: Bessie fires. If there is a target at Bessie's current position, it is hit and destroyed. It cannot be hit again.

Before Bessie starts, you are allowed to modify at most one command in the sequence. What is the maximum number of targets Bessie can hit?

## Input Format

The first line contains $T$ and $C$.

The next line contains $T$ positions of the targets, all different integers within the range $[-C, C]$.

The next line contains a sequence of $C$ commands, consisting only of the characters `F`, `L`, and `R`.

## Output Format

Output the maximum number of targets Bessie can hit after modifying at most one command.

## Sample Input and Output

### Sample Input #1

```
3 7
0 -1 1
LFFRFRR
```

### Sample Output #1

```
3
```

### Sample Input #2

```
1 5
0
FFFFF
```

### Sample Output #2

```
1
```

### Sample Input #3

```
5 6
1 2 3 4 5
FFRFRF
```

### Sample Output #3

```
3
```

## Notes

### Sample Explanation 1

If you do not modify the command sequence, Bessie will hit two targets.

| Command | Position | Number of Targets Hit |
| :----------- | :----------- | :----------- |
| Start | 0 | 0 |
| L | -1 | 0 |
| F | -1 | 1 |
| F | -1 | 1 (cannot destroy a target more than once) |
| R | 0 | 1 |
| F | 0 | 2 |
| R | 1 | 2 |
| R | 2 | 2 |

If you change the last command from `R` to `F`, Bessie will hit three targets:

| Command | Position | Number of Targets Hit |
| :----------- | :----------- | :----------- |
| Start | 0 | 0 |
| L | -1 | 0 |
| F | -1 | 1 |
| F | -1 | 1 (cannot destroy a target more than once) |
| R | 0 | 1 |
| F | 0 | 2 |
| R | 1 | 2 |
| F | 1 | 3 |

### Sample Explanation 2

If the command sequence is not modified, the only target at position $0$ will be hit.

Since a target cannot be destroyed multiple times, the answer is $1$.

### Test Case Properties

- Test cases $4-6$ satisfy $T, C \le 1000$.
- Test cases $7-15$ have no additional restrictions.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
