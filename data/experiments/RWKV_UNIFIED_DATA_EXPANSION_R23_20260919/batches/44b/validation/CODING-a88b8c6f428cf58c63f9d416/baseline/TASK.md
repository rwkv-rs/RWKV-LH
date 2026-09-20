As the New Year 2009 approaches, JSK decides to drive to visit all his friends in the town. Since he has a friend on every street, he considers how to make his journey as short as possible. He quickly realizes that the shortest way is to traverse all streets exactly once. Naturally, he wants to return to his starting point at the end of the journey, which is his parents' house.

JSK plans his town tour: the streets are numbered from $1$ to $n$, and the intersections are numbered from $1$ to $m$. No intersection connects more than $44$ streets. All intersections have distinct numerical identifiers.

Each street connects exactly two intersections, and no two streets share the same number. If more than one such tour path exists, the one with the lexicographically smallest sequence of street numbers is chosen.

Since JSK cannot find even a single street, he asks you to write a program to find the shortest tour path. If no such path exists, print a message indicating so. Assume JSK lives at the intersection with the smaller number connected to street $1$.

Every street in the town is identical (not a dead end), and any two streets are reachable from each other. The streets are narrow, so once a car enters a street, it cannot turn back.

## Input Format

Each line includes three integers $x, y, z$. If $x > 0$ and $y > 0$, they represent the intersection numbers connected to the street numbered $z$. If $x = 0$ and $y = 0$, it marks the end of the input.

## Output Format

The output file contains one line describing JSK's town tour (a sequence of street numbers separated by spaces). If no satisfying tour route is found, the line should contain the message: `Round trip does not exist`.

## Sample Input and Output

### Sample Input #1

```
1 2 1
2 3 2
3 1 6
1 2 5
2 3 3
3 1 4
0 0 0
```

### Sample Output #1

```
1 2 3 5 4 6
```

### Sample Input #2

```
1 2 1
2 3 2
1 3 3
2 4 4
0 0 0
```

### Sample Output #2

```
Round trip does not exist
```

## Notes

### Data Range

$1 \le n \le 1994$, $1 \le m \le 43$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
