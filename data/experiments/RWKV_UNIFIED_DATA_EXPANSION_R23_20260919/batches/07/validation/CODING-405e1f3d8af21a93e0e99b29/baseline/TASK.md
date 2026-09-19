Many years ago, Country A developed a missile system to intercept missiles launched by hostile forces.

This system could launch a single missile to intercept multiple missiles in order from near to far, with non-increasing heights.

However, scientists have now discovered that this defense system is not powerful enough, so they have invented another missile system.

The new system can launch a single missile to intercept more missiles from near to far.

When this system is activated, it first selects an enemy missile to intercept, then intercepts a farther missile with a lower height, followed by intercepting a missile that is even farther but with a higher height... and so on. The odd-numbered intercepted missiles are farther and higher than the previous one, while the even-numbered intercepted missiles are farther and lower than the previous one.

Given a list of missile heights from near to far, calculate the maximum number of missiles that the new system can intercept with a single launch.

## Input Format

The first line contains an integer $n$, representing the number of enemy missiles. The next line contains $n$ integers, representing the heights of the missiles from near to far.

## Output Format

A single integer representing the maximum number of missiles that can be intercepted.

## Sample Input and Output

### Sample Input #1

```
4
5 3 2 4
```

### Sample Output #1

```
3
```

## Notes

$1 \leq n \leq 10^3$, $1 \leq \text{missile height} \leq 10^9$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
