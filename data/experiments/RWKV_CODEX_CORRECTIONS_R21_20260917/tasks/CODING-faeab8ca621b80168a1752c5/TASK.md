You have $k$ different pieces of furniture that need to be placed in $n$ different rooms. Assuming each room is large enough and considering only which room each piece of furniture is in (without considering the arrangement within the room), there are a total of $n^k$ different ways to arrange them (note, not $k^n$).

Arranging furniture is also a science, at least it shouldn't be done randomly. For each arrangement, we can assign a score. For example, placing a dining table in a bathroom, or having two beds in one bedroom while another bedroom has none, would result in a lower score. Since this score is not independent for each piece of furniture and each room, we will input the scores for all $n^k$ possible arrangements.

You are in the mood to change the layout of the rooms. Given an initial arrangement, you will repeat the following operation $T$ times: each time, you will randomly select a piece of furniture and move it to any other room. Each round has $k(n-1)$ decisions (the number of ways to choose a piece of furniture multiplied by the number of ways to choose another room), so there are a total of $k^T(n-1)^T$ decisions. You need to calculate the sum of the scores for each decision after the arrangement.

Moreover, we will provide $q$ queries, each inputting the initial arrangement and $T$, and you need to answer the sum of the scores for $k^T(n-1)^T$ decisions **online** (modulo $P$). See the input and output formats for details.

We define the numbering of an arrangement as follows:

We number the furniture from 0 to $k-1$ and the rooms from 0 to $n-1$. Suppose in a certain arrangement, the $i$-th piece of furniture is placed in the $p_i$-th room, then the number of this arrangement is defined as $\sum_{i=0}^{k-1} p_i n^i$. It can be found that the numbers of all $n^k$ arrangements are exactly the different integers from 0 to $n^k - 1$.

Additionally, let $P=998244353$.

## Input Format

The first line inputs three positive integers $n, k, q$.

The next $n^k$ lines each input a positive integer less than $P$, representing the scores of the arrangements numbered from 0 to $n^k - 1$ in order.

The next $q$ lines each input two non-negative integers. Suppose the input for a line is $a, b$ (guaranteed $0 \leq a < n^k, 0 \leq b < P$), then the initial arrangement number for this query is $a$, and $T=b \cdot r \bmod P$, where $r$ is the number you last output (for the first query, it is 1).

Adjacent numbers within the same line are separated by a space.

It is guaranteed that $n \geq 2$, $k \geq 1$; $n^k \leq 10^6$; $q \leq 5 \times 10^5$.

## Output Format

For each query, output a line containing a non-negative integer, representing the result of the sum of the scores modulo $P$.

## Sample Input and Output

### Input Sample #1

```
2 3 3
1
10
100
1000
998244245
100000
1000000
10000000
0 1
0 1
1 233
```

### Output Sample #1

```
2
2202003
444957911
```

## Notes/Hints

### Sample Explanation

In the first query, the initial arrangement number is 0, and $T=1$.

Initially, the 0th piece of furniture is in room 0, the 1st piece of furniture is in room 0, and the 2nd piece of furniture is in room 0. After 1 operation, the possible situations are:

- Move the 0th piece of furniture to room 1, the subsequent arrangement number is 1, with a score of 10;
- Move the 1st piece of furniture to room 1, the subsequent arrangement number is 2, with a score of 100;
- Move the 2nd piece of furniture to room 1, the subsequent arrangement number is 4, with a score of 998244245.

Therefore, the total score for all situations is 998244355, which modulo $P$ is 2.

In the second query, the initial arrangement number is 0, and $T=2$.

Initially, the 0th piece of furniture is in room 0, the 1st piece of furniture is in room 0, and the 2nd piece of furniture is in room 0. After 2 operations, the possible situations are:

- Move the 0th piece of furniture to room 1, then move the 0th piece of furniture to room 0, the subsequent arrangement number is 0, with a score of 1;
- Move the 0th piece of furniture to room 1, then move the 1st piece of furniture to room 1, the subsequent arrangement number is 3, with a score of 1000;
- Move the 0th piece of furniture to room 1, then move the 2nd piece of furniture to room 1, the subsequent arrangement number is 5, with a score of 100000;
- Move the 1st piece of furniture to room 1, then move the 0th piece of furniture to room 1, the subsequent arrangement number is 3, with a score of 1000;
- Move the 1st piece of furniture to room 1, then move the 1st piece of furniture to room 0, the subsequent arrangement number is 0, with a score of 1;
- Move the 1st piece of furniture to room 1, then move the 2nd piece of furniture to room 1, the subsequent arrangement number is 6, with a score of 1000000;
- Move the 2nd piece of furniture to room 1, then move the 0th piece of furniture to room 1, the subsequent arrangement number is 5, with a score of 100000;
- Move the 2nd piece of furniture to room 1, then move the 1st piece of furniture to room 1, the subsequent arrangement number is 6, with a score of 1000000;
- Move the 2nd piece of furniture to room 1, then move the 2nd piece of furniture to room 0, the subsequent arrangement number is 0, with a score of 1.

Therefore, the total score for all situations is 2202003, which modulo $P$ is 2202003.

In the third query, the initial arrangement number is 1, and $T=513066699$. Initially, the 0th piece of furniture is in room 1, the 1st piece of furniture is in room 0, and the 2nd piece of furniture is in room 0.

... (omitting at least $3^{513066699}$ lines)

### Copyright Information
From THUPC (THU Programming Contest) 2019.

Problem solutions and other resources can be found at https://github.com/wangyurzee7/THUPC2019.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
