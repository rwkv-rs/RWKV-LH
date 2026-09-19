A brain can be conceptualized as an undirected graph, where each region is represented as a node. Currently, all regions of this brain are in a state of sleep.

Scientific research suggests that a sleeping region can wake up if it is connected to at least 3 awake regions for more than 1 year.

Now, scientists will manually awaken 3 regions.

You are given the number of regions $n$, the number of edges $m$, and 3 uppercase letters indicating the 3 initially awake regions. Additionally, there are $m$ lines, each containing 2 uppercase letters that represent two connected regions.

If the entire brain can wake up after $x$ years, output:

```
WAKE UP IN, x, YEARS
```

The word `YEARS` must be in plural form, regardless of whether $x$ is singular or plural.

If it is impossible for the brain to wake up, output:

```
THIS BRAIN NEVER WAKES UP
```

Note that the nodes are not numbered in alphabetical order.

By [@dengziyue](/user/387840)

## Input and Output Example

### Input Example #1

```
6
11
HAB
AB
AC
AH
BD
BC
BF
CD
CF
CH
DF
FH
```

### Output Example #1

```
WAKE UP IN, 3, YEARS
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
