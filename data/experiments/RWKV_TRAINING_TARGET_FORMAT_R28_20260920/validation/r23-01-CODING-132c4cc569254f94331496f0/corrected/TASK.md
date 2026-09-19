Description
-----

Given $12$ equal-length, colored sticks. Determine the number of essentially different cubes that can be formed. There are at most $6$ different colors.

Two cubes, $A$ and $B$, are essentially different if $A$ cannot be transformed into $B$ by rotation.

Input
-----

The first line contains an integer $T$, representing the number of test cases.

The following $T$ lines each contain $12$ integers, representing the colors of the $12$ sticks in that test case.

Output
-----

Output a total of $T$ lines.  

For each test case, output one integer on a new line. This integer represents the number of essentially different cubes that can be formed with the given $12$ sticks.

## Input and Output Example

### Input Example #1

```
3
1 2 2 2 2 2 2 2 2 2 2 2
1 1 2 2 2 2 2 2 2 2 2 2
1 1 2 2 3 3 4 4 5 5 6 6
```

### Output Example #1

```
1
5
312120
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
