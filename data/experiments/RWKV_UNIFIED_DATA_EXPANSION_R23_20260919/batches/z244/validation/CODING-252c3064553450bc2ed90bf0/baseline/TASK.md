Given an array $a$, consisting of $n$ integers, find: $\max\limits_{1 \le i < j \le n} LCM(a_i,a_j),$ where $LCM(x, y)$ is the smallest positive integer that is divisible by both $x$ and $y$. For example, $LCM(6, 8) = 24$, $LCM(4, 12) = 12$, $LCM(2, 3) = 6$.

## Time Limit and Memory Limit

Time Limit: 1 second
Memory Limit: 256 megabytes

## Input Specification

The first line contains an integer $n$ ($2 \le n \le 10^5$) — the number of elements in the array $a$. The second line contains $n$ integers $a_1, a_2, \dots, a_n$ ($1 \le a_i \le 10^5$) — the elements of the array $a$.

## Output Specification

Print one integer, the maximum value of the least common multiple of two elements in the array $a$.

## Examples

### Input #1

3
13 35 77


### Output #1

1001

### Input #2

6
1 2 4 8 16 32


### Output #2

32

## Note

None

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
