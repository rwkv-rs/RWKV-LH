Due to the large amount of official test data, to avoid excessive resource consumption, a portion of the official data has been selected as the test data for this problem.

## Problem Description

The Clown has returned to Gotham City to execute a sinister plan. Gotham City has $N$ intersections (numbered from $1$ to $N$) and $M$ roads (numbered from $1$ to $M$). A road connects two different intersections, and there is at most one road between any two intersections.

To carry out his evil plan, the Clown needs to complete an odd cycle in the city. Formally, an odd cycle is a sequence like $S, s_1, s_2, \ldots, s_k, S$ (where $k$ is even), where $S$ and $s_1$, $s_k$ and $S$, and for all $1 < i \leq k$, $s_{i-1}$ and $s_i$ are directly connected by a road.

However, the police have controlled some streets in the city. On the $i$-th day, the police control all streets with numbers in the range $[l_i, r_i]$, and the Clown cannot pass through these streets. Fortunately, the Clown has bribed an insider at the police station and knows the police's plan for controlling the streets for the next $Q$ days. Now, the Clown wants to know on which days his evil plan can be executed.

## Input Format

The first line of input contains three integers $N, M, Q$.

The next $M$ lines, the $i$-th line contains two integers $u, v$ (guaranteed $u \neq v$), describing the road numbered $i$ that connects intersections $u$ and $v$. It is guaranteed that there is at most one road between any two intersections.

The next $Q$ lines, the $i$-th line contains two integers $l_i, r_i$, indicating that the police will control all streets with numbers in the range $[l_i, r_i]$ on the $i$-th day.

## Output Format

Output $Q$ lines.

On the $i$-th line, if the Clown's plan can be executed on the $i$-th day, output `YES`, otherwise output `NO`.

## Sample Input and Output

### Input Sample #1

```
6 8 2
1 3
1 5
1 6
2 5
2 6
3 4
3 5
5 6
4 8
4 7
```

### Output Sample #1

```
NO
YES
```

## Notes

### Sample Explanation

![Image](https://cdn.luogu.com.cn/upload/image_hosting/qr5q8ha4.png)

### Subtasks

All data satisfy: $1 \leq N, M, Q \leq 2 \times 10^5$.

- Subtask 1 (6 points): $1 \leq N, M, Q \leq 200$;
- Subtask 2 (8 points): $1 \leq N, M, Q \leq 2 \times 10^3$;
- Subtask 3 (25 points): $\forall i \in [1, Q]$, $l_i = 1$;
- Subtask 4 (10 points): $\forall i \in [1, Q]$, $l_i \leq 200$;
- Subtask 5 (22 points): $Q \leq 2 \times 10^3$;
- Subtask 6 (29 points): No additional constraints.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
