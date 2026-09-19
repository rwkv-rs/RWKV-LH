##### Program Type

This problem requires us to write a program to simulate an election.

##### Input

You will first receive $c$ and $n$, indicating there are $c$ candidates and $n$ ballots.

The next $n$ lines each contain $c$ numbers, representing a ballot; each sequence of numbers on a ballot shows the voter's preference for the candidates, such as:

```
1 3 2
```

This means that the voter's first choice is candidate $1$, second choice is candidate $3$, and third choice is candidate $2$.

On each ballot, every number from $1$ to $c$ will **appear exactly once**; otherwise, it is an invalid ballot. Invalid ballots do not participate in the election, but you need to count their total number as $bad\_tot$.

##### Election

Define the winning vote count $win\_tot$, such that $win\_tot=\left\lceil\dfrac{(n-bad\_tot)}{2}\right\rceil$.

1. First, count the votes for each candidate. If one (or more) candidates receive more votes than $win\_tot$, then this (or these) candidate(s) is the winner, and you can exit the loop.

2. Remove any candidate with the lowest number of votes (they have failed). Therefore, the voters who selected this candidate must now choose their next preference. Continue the loop.

##### Output

First output the dataset for the test cases, then output the number of invalid ballots, and finally, the winner(s) (there might be multiple, in which case refer to the example).

Note: In the lines for "invalid ballots" and "winner(s)", prefix with $3$ spaces, though this is not shown in the example.

By **dengziyue**

## Input/Output Sample

### Input Sample #1

```
3 12
1 2 4
1 3 2
3 2 1
3 2 1
1 2 3
2 3 1
3 2 1
3 1 1
3 2 1
1 2 3
1 3 2
2 3 1
3 12
1 2 4
1 3 2
3 2 1
3 2 1
1 2 3
2 3 1
3 2 1
3 1 1
3 2 1
1 2 3
1 3 2
2 1 3
4 15
4 3 1 2
4 1 2 3
3 1 4 2
1 3 2 4
4 1 2 3
3 4 2 1
2 4 3 1
3 2 1 4
3 1 4 2
1 4 2 3
3 4 1 2
3 2 1 4
4 1 3 2
3 2 1 4
4 2 1 4
0 0
```

### Output Sample #1

```
Election #1
2 bad ballot(s)
Candidate 3 is elected.
Election #2
2 bad ballot(s)
The following candidates are tied: 1 3
Election #3
1 bad ballot(s)
Candidate 3 is elected.
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
