At night, the sky is dark and stormy, with rain pouring down relentlessly.

Lucy wants to catch some raindrops, but she only has limited tools. She has a set of pillars of different heights to catch the raindrops. Each pillar has an integer height and a width of $1$. After arranging the pillars, she will use other tools to clamp the pillars, allowing the raindrops to be stored in the gaps between the pillars. You can assume that the number of raindrops is infinite.

For example, if Lucy has five pillars with heights $(1, 5, 2, 1, 4)$, she can arrange them like this:

```
 *   
 *  *
 *  *
 ** *
*****
```

This will catch $5r$ raindrops ($r$ represents $1$ unit of raindrops).

**For convenience, we define $r$ as the unit of raindrops.**

```
 *   
 *RR*
 *RR*
 **R*
*****
```

Of course, she can also arrange the pillars like this, which can catch $6r$ raindrops.

```
 *   
 *RR*
 *RR*
**RR*
*****
```

Another example, if the heights of the pillars are $(5, 1, 5, 1, 5)$, Lucy can catch $8r$ raindrops.

```
*R*R*
*R*R*
*R*R*
*R*R*
*****
```

One last example, if the heights of the pillars are $(5, 1, 4, 1, 5)$, she can catch $9r$ raindrops.

```
*RRR*
*R*R*
*R*R*
*R*R*
*****
```

Lucy has $n$ pillars with heights $h_1, h_2, ..., h_n$. She wants to know all possible amounts of raindrops (in units of $r$) that can be caught in all possible arrangements. (See the sample explanations for details)

## Input Format

The first line contains an integer $n$, representing the number of pillars.

The second line contains $n$ integers $h_i$, representing the heights of the pillars.

## Output Format

Output a single line containing all possible amounts of caught raindrops (in units of $r$) in ascending order.

## Sample Input and Output

### Sample Input #1

```
5
1 5 2 1 4
```

### Sample Output #1

```
0 1 2 3 4 5 6 8 
```

### Sample Input #2

```
5
5 1 5 1 5
```

### Sample Output #2

```
0 4 8
```

### Sample Input #3

```
5
5 1 4 1 5
```

### Sample Output #3

```
0 1 3 4 5 6 7 8 9
```

## Notes

### Sample Explanations

Refer to the three examples in the problem description.

### Data Range and Constraints

**This problem uses multiple test cases bundled together, with a total of $3$ subtasks.**

- Subtask 1 (20 points): $2 \le n \le 10$;
- Subtask 2 (40 points): $2 \le n \le 50$;
- Subtask 3 (40 points): $2 \le n \le 500$, $1 \le h_i \le 50$.

For all test cases, it is guaranteed that $2 \le n \le 500$ and $1 \le h_i \le 50$.

Source: [CCO 2017](https://cemc.math.uwaterloo.ca/contests/computing/2017/) Day2 "[Rainfall Capture](https://cemc.math.uwaterloo.ca/contests/computing/2017/stage%202/day2.pdf)".

Note: Translation from [LOJ](https://loj.ac/problem/2753).

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
