You are given a set of N sticks and are required to partition them into groups of exactly 3 sticks each. While doing so, you can leave out any number of sicks out of these groups (in particular, no groups may be formed). One condition needs to be met: sticks in each group need to form a triangle. A triangle can be constructed if sum of any two sticks lengths is greater than the third length.

Your are required to partition the sticks so that the sum of triangle areas from all the groups is maximized.

## Input Format

Very first line of the input contains integer T: number of test cases (1 <= T <= 5).

For each test case, first line contains integer N: number of sticks. (1 <= N <= 15).

Second line contains N space separated integers: the lengths l $ _{i} $ of the sicks. (1 <= l $ _{i} $ <= 10^3, 1 <= i <= N).

## Output Format

For each test case, output the maximal area in a separate line. Round value to exactly 6 decimal places. **Always** print exactly 6 decimal places.

## Sample Input and Output

### Sample Input #1

```
\n3\n3\n7 8 5 \n4\n7 8 6 3 \n3\n7 2 1\n\n
```

### Sample Output #1

```
\n17.320508\n20.333163\n0.000000
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
