You are given array $a_1, a_2, \dots, a_n$. You need to split it into $k$ subsegments (so every element is included in exactly one subsegment). The weight of a subsegment $a_l, a_{l+1}, \dots, a_r$ is equal to $(r - l + 1) \cdot \max\limits_{l \le i \le r}(a_i)$. The weight of a partition is a total weight of all its segments. Find the partition of minimal weight.

## Time Limit and Memory Limit

Time Limit: 5 seconds
Memory Limit: 512 megabytes

## Input Specification

The first line contains two integers $n$ and $k$ ($1 \le n \le 2 \cdot 10^4$, $1 \le k \le \min(100, n)$) — the length of the array $a$ and the number of subsegments in the partition. The second line contains $n$ integers $a_1, a_2, \dots, a_n$ ($1 \le a_i \le 2 \cdot 10^4$) — the array $a$.

## Output Specification

Print single integer — the minimal weight among all possible partitions.

## Examples

### Input #1

4 2
6 1 7 4


### Output #1

25


### Input #2

4 3
6 1 7 4


### Output #2

21


### Input #3

5 4
5 1 5 1 5


### Output #3

21

## Note

The optimal partition in the first example is next: $6$ $1$ $7$ $\bigg|$ $4$. The optimal partition in the second example is next: $6$ $\bigg|$ $1$ $\bigg|$ $7$ $4$. One of the optimal partitions in the third example is next: $5$ $\bigg|$ $1$ $5$ $\bigg|$ $1$ $\bigg|$ $5$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
