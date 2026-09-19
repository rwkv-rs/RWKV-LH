There is a railway station in a city with tracks laid out as shown in a diagram. There are `n` train cars entering the station from direction A, numbered 1 to `n` in the order they arrive. Your task is to determine if it's possible for them to leave the station via direction B in a specific sequence. For example, the sequence (5 4 1 2 3) is not possible, but (5 4 3 2 1) is possible.

To reorganize the train cars, you can use an intermediate station C. This is a station where you can park any number of cars, but since it is end-capped, cars must exit C in the reverse order of their entry. Once a car is moved from A to C, it cannot return to A; similarly, once a car is moved from C to B, it cannot return to C. This means that at any time, only two moves are possible: A to C and C to B.

For each set of data, the first line is an integer $N$. The following data lines each contain `N` numbers, representing the sequence in which the cars leave the stack (1 to N). The final data set contains just a single integer `0`. An empty line should be output after each data set.

The last data set has $N=0$, and nothing should be output.

$n \leq 1000$

## Input and Output Samples

### Input Sample #1

```
5
1 2 3 4 5
5 4 1 2 3
0
6
6 5 4 3 2 1
0
0
```

### Output Sample #1

```
Yes
No

Yes
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
