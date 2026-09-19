You have suddenly acquired a large house, which contains several rooms. In fact, your house can be seen as a grid-shaped rectangle consisting of $n \times m$ cells, where each cell represents either a room or a pillar. Initially, walls separate adjacent cells.

You want to knock down some of the walls between adjacent rooms so that all rooms can reach each other. During this process, you must not breach the house or knock down walls around pillars. Also, you do not want to make it difficult to catch thieves in your house, so you aim to ensure that there is only one path between any two rooms. Now, you wish to count the number of feasible schemes, with the answer modulo $10^9$.

## Input Format

The first line contains two integers $n$ and $m$.

The next $n$ lines each contain $m$ characters, either `.` or `*`, where `.` represents a room and `*` represents a pillar.

## Output Format

A single line containing an integer, representing the number of valid schemes modulo $10^9$.

## Sample Input and Output

### Sample Input #1

```
2 2
..
..
```

### Sample Output #1

```
4
```

### Sample Input #2

```
2 2
*.
.*
```

### Sample Output #2

```
0
```

## Notes/Hints

### Data Size and Constraints

- For $20\%$ of the data, $n, m \le 3$.
- For $50\%$ of the data, $n, m \le 5$.
- $40\%$ of the data has $\min(n, m) \le 3$.
- $30\%$ of the data has no pillars.
- For $100\%$ of the data, $1 \le n, m \le 9$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
