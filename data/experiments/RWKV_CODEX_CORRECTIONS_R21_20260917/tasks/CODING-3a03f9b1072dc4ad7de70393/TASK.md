Define a run in a string $|S|$ as an internal segment that cannot be extended on either side, which is a **periodic substring** and the period must appear at least twice completely.

Formally, a run is a triplet $(i, j, p)$ where $p$ is the minimum period of $S[i..j]$, $j - i + 1 \ge 2p$, and satisfies the following two conditions:

+ Either $i = 1$, or $S[i-1] \ne S[i-1+p]$;
+ Either $j = n$, or $S[j+1] \ne S[j+1-p]$.

Given a string $S$, find all its runs.

## Input Format

A single line containing a string $S$, guaranteed to be composed only of lowercase letters.

## Output Format

The first line contains an integer $m$, representing the number of runs.

The next $m$ lines each contain three integers describing a run:

+ The position of the first character of the run
+ The position of the last character of the run
+ The length of the minimum cycle of the run

You should sort all runs by the position of the first character as the primary key and the position of the last character as the secondary key.

## Sample Input and Output

### Input Sample #1

```
aababaababb
```

### Output Sample #1

```
7
1 2 1
1 10 5
2 6 2
4 9 3
6 7 1
7 10 2
10 11 1
```

## Notes/Hints

For $60\%$ of the data, $|S| \le 2 \times 10^5$.

For $100\%$ of the data, $|S| \le 10^6$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
