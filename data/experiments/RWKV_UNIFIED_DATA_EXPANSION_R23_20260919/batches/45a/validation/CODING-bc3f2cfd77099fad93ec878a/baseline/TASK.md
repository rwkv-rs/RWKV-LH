Due to conflicts arising from resource disputes, countries A and B are on the brink of war. The spy agency of country A has managed to obtain the communication network layout of country B, where each city can be considered a node, and there are undirected edges between certain nodes, indicating that these cities can communicate directly with each other. Country A plans to strike first by using nuclear weapons to destroy a middle city M, thereby severing the connection between two important cities S and T in country B. Specifically, after removing city M from the graph, S and T become disconnected. However, due to the strong defenses of country B, such a nuclear strike can only be successful once and can only destroy one city.

## Problem Description

The leader of country A has proposed many combat strategies. As the chief computer scientist of country A, your task is to write a program to determine the feasibility of these strategies.

## Input Format

The first line of the input file contains two integers N and M, representing the number of cities in country B and the number of city pairs that can communicate directly. The next M lines each include two integers Ci and Di (1 ≤ Ci, Di ≤ N and Ci ≠ Di), indicating that cities Ci and Di can communicate directly. The input data guarantees that each pair (Ci, Di) appears at most once.

The next line is an integer Q, representing the number of strategies proposed by the leader of country A. The following Q lines each include three integers Si, Ti, Mi (1 ≤ Si, Ti, Mi ≤ N, and the three numbers are distinct), indicating the content of the strategy to cut off the connection between Si and Ti by destroying Mi.

## Output Format

Output Q lines, indicating the feasibility of the corresponding strategies. If destroying Mi results in Si and Ti being unable to communicate, the strategy is feasible, and you should output "yes" on the ith line; otherwise, output "no".

## Sample Input and Output

### Input Sample #1

```
5 6
1 2
1 3
2 3
3 4
3 5
4 5
3
1 5 3
1 5 4
4 5 3
```

### Output Sample #1

```
yes
no
no
```

## Notes

For 30% of the data, 1 ≤ N ≤ 100, 1 ≤ Q ≤ 100.

For 100% of the data, 1 ≤ N ≤ 20000, 1 ≤ M ≤ 100000, 1 ≤ Q ≤ 100000.

The input data guarantees that any two points in the original graph are connected.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
