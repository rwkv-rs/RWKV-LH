The space station has $C(1≤C≤5)$ compartments, each of which can hold up to $2$ people. You need to distribute $S(1≤S≤2·C)$ people into these $C$ compartments. The $i^{th}$ person has a weight of $Wi(1≤Wi≤1000)$. The objective is to minimize 

$$F = \sum_{i=1}^C|CM_i-AM|$$

where $F$ represents the imbalance. $CM_i$ is the sum of weights of people in compartment $i$, and $AM$ is the average sum of weights of people across all compartments. Output a configuration that minimizes $F$ and the corresponding value of $F$.

Note: The output format is somewhat unconventional, so please refer to the original problem statement for details.

## Input and Output Example

### Input Example #1

```
2 3
6 3 8
3 5
51 19 27 14 33
5 9
1 2 3 5 7 11 13 17 19
```

### Output Example #1

```
Set #1
0: 6 3
1: 8
IMBALANCE = 1.00000
Set #2
0: 51
1: 19 27
2: 14 33
IMBALANCE = 6.00000
Set #3
0: 1 17
1: 2 13
2: 3 11
3: 5 7
4: 19
IMBALANCE = 11.60000
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
