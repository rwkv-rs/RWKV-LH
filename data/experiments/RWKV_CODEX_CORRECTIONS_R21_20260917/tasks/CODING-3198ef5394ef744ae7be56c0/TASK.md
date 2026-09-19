There is an airport with two aircraft queues (designated as $W$ and $E$), but only one take-off runway.

At each time step, a number of airplanes arrive at queues $W$ or $E$ and begin waiting for take-off. At any given moment, the number assigned to an airplane corresponds to the number of planes currently waiting ahead of it (i.e., $0, 1, 2, \ldots$). Only one plane can take off at any given moment.

Your task is to choose a plane to take off from either $W$ or $E$ at each moment, such that the maximum number assigned to any plane at any given moment is minimized.

## Input and Output Example

### Input Example #1

```
3
1
1 1
3
3 2
0 3
2 0
6
0 1
1 1
1 2
1 1
1 1
6 0
```

### Output Example #1

```
0
3
5
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
