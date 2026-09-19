### Problem Description

Given the coordinates of $n$ ice floes and the distance $d$ that a penguin can jump, each ice floe has four attributes: $x$ coordinate, $y$ coordinate, the initial number of penguins on it, and the maximum number of times a penguin can jump *off* of it. Determine which ice floes can allow all penguins to jump onto them.

### Input Format

The first line contains a positive integer $T$, representing the number of test cases.

For each test case, the first line contains an integer $n$ and a floating-point number $d$, representing the total number of ice floes and the maximum jumping distance of a penguin.

The following $n$ lines each contain four integers, representing the coordinates of an ice floe, the initial number of penguins on the floe, and the maximum number of times any penguin can jump off the floe.

### Output Format

For each test case, output several numbers, which are the indices of the ice floes that can allow all penguins to jump onto them. If no such ice floe exists, output `-1`.

## Sample Input

### Input Sample #1

```
2
5 3.5
1 1 1 1
2 3 0 1
3 5 1 1
5 1 1 1
5 4 0 1
3 1.1
-1 0 5 10
0 0 3 9
2 0 1 1
```

### Output Sample #1

```
1 2 4
-1
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
