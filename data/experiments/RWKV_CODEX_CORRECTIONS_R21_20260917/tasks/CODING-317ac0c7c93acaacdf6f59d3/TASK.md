On the grassland, there are $n$ snakes numbered as $1, 2, \ldots, n$. Initially, each snake has a stamina value $a_i$. We say that the snake numbered $x$ is stronger than the snake numbered $y$ if and only if their current stamina values satisfy $a_x > a_y$, or $a_x = a_y$ and $x > y$.

These snakes will engage in a battle that will last for several rounds. In each round, the snake with the highest strength (stamina) has the choice to eat or not to eat the snake with the lowest strength:

1. If it chooses to eat, the strongest snake's stamina will be reduced by the weakest snake's stamina, and the weakest snake will be eliminated from further battles. Then, the next round begins.
2. If it chooses not to eat, the battle immediately ends.

Each snake aims to eat as many other snakes as possible while ensuring it is not eaten (obviously, a snake will not choose to eat itself).

Now, assuming that each snake is smart enough, please determine how many snakes will be left after the battle.

This problem contains multiple sets of data. For the first set of data, the stamina values of all snakes will be provided as input. For each subsequent set of data, some of the stamina values will be modified relative to the previous set.

## Input Format

The first line contains a positive integer $T$, indicating the number of data sets.  
For the first set of data, the first line contains a positive integer $n$, and the second line contains $n$ non-negative integers representing $a_i$.  
For the second to the $T$-th set of data, each set:  
The first line contains a non-negative integer $k$ indicating the number of snakes whose stamina is modified.  
The second line contains $2k$ integers, each pair of integers forming a tuple $(x, y)$, indicating that the value of $a_x$ is changed to $y$. A position may be modified multiple times, with the last modification taking effect.

## Output Format

Output $T$ lines, each containing an integer representing the number of snakes that remain alive.

## Sample Input and Output

### Input Sample #1

```
2
3
11 14 14
3
1 5 2 6 3 25
```

### Output Sample #1

```
3
1
```

### Input Sample #2

```
2
5
13 31 33 39 42
5
1 7 2 10 3 24 4 48 5 50
```

### Output Sample #2

```
5
3
```

### Input Sample #3

```
See attached file snakes/snakes3.in
```

### Output Sample #3

```
See attached file snakes/snakes3.ans
```

### Input Sample #4

```
See attached file snakes/snakes4.in
```

### Output Sample #4

```
See attached file snakes/snakes4.ans
```

## Notes

**[Sample #1 Explanation]**

For the first set of data, in the first round, the snake #3 is the strongest and the snake #1 is the weakest. If snake #3 chooses to eat, it will be eaten by snake #2 in the second round. Therefore, snake #3 chooses not to eat in the first round, and all three snakes will survive.

For the second set of data, the stamina values of the three snakes become $5, 6, 25$. In the first round, snake #3 is the strongest and snake #1 is the weakest. If it chooses to eat, snake #3's stamina will become $20$, which is still the highest in the second round and it can eat snake #2. Therefore, snake #3 will choose to eat in both rounds, and only one snake will survive.

**[Data Range]**

For $20\%$ of the data, $n = 3$.  
For $40\%$ of the data, $n \le 10$.  
For $55\%$ of the data, $n \le 2000$.  
For $70\%$ of the data, $n \le 5 \times 10^4$.  
For $100\%$ of the data: $3 \le n \le 10^6$, $1 \le T \le 10$, $0 \le k \le 10^5$, $0 \le a_i, y \le 10^9$. Ensure that $a_i$ is sorted in non-decreasing order for each set of data (including all modifications).

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
