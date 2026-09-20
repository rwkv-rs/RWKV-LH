1. wqs loves simulation flying.
2. clj has established Divine Master Airlines, but since clj is also busy playing games, the company's affairs are managed by you.

Note: The background is just used for setting the context and does not correspond to real or simulation flying.

## Problem Description

Divine Master Airlines has launched a passenger aerobatic flying service. Each flight lasts for \( n \) units of time, and during each unit of time, an aerobatic maneuver can be performed. There are \( k \) types of maneuvers available, each with a thrill level \( c_i \). If the same maneuver is performed consecutively, passengers will get bored. Therefore, the value of a maneuver is defined as the time since the last occurrence of that maneuver multiplied by \( c_i \), and if it is the first time performing that maneuver, the value is \( 0 \). Arrange a plan to maximize the total value.

## Input Format

The first line contains two integers, \( n \) and \( k \), as described above.
The second line contains \( k \) integers representing the thrill levels \( c_i \) of the \( k \) types of maneuvers.

## Output Format

A single line containing one integer, representing the maximum total value.

## Sample Input and Output

### Input Sample #1

```
5 2
2 2
```

### Output Sample #1

```
12
```

## Notes/Hints

### Data Size and Constraints

- For \( 10\% \) of the test cases, \( n \leq 20 \), \( k \leq 3 \).
- For \( 100\% \) of the test cases, \( 1 \leq n \leq 10^3 \), \( 1 \leq k \leq 300 \), \( 0 \leq c_i \leq 10^3 \).

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
