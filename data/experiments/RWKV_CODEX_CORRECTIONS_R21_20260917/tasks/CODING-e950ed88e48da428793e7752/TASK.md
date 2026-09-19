A pair of numbers has a unique least common multiple (LCM), but a single LCM can correspond to multiple pairs of numbers.

-----

Given a number $n$ $(0 \le n \le 2 \times 10^9)$, determine the number of pairs of numbers whose least common multiple equals $n$.

----

Simplified Problem Statement: For a given number $n$ $(0 \le n \le 2 \times 10^9)$, determine:
$$\sum_{i=1}^n\sum_{j=i+1}^n[lcm(i,j)=n]$$

----

## Input Format

Continuously input a number $n$ until $n=0$ is encountered, which stops the input.

## Output Format

For each input number $n$, output two numbers $n$ and $c$ on a new line, separated by a space, where $c$ is the answer to the problem.

## Input and Output Example

### Input Example #1

```
2
12
24
101101291
0
```

### Output Example #1

```
2 2
12 8
24 11
101101291 5
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
