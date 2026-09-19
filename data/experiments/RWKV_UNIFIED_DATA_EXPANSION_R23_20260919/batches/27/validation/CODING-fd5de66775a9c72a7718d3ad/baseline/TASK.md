Your task is to calculate the number of arrays such that: each array contains $n$ elements;  each element is an integer from $1$ to $m$;  for each array, there is exactly one pair of equal elements;  for each array $a$, there exists an index $i$ such that the array is strictly ascending before the $i$-th element and strictly descending after it (formally, it means that $a_j < a_{j + 1}$, if $j < i$, and $a_j > a_{j + 1}$, if $j \ge i$).

## Time Limit and Memory Limit

Time Limit: 2 seconds
Memory Limit: 512 megabytes

## Input Specification

The first line contains two integers $n$ and $m$ ($2 \le n \le m \le 2 \cdot 10^5$).

## Output Specification

Print one integer — the number of arrays that meet all of the aforementioned conditions, taken modulo $998244353$.

## Examples

### Input #1

3 4


### Output #1

6


### Input #2

3 5


### Output #2

10


### Input #3

42 1337


### Output #3

806066790


### Input #4

100000 200000


### Output #4

707899035

## Note

The arrays in the first example are: $[1, 2, 1]$;  $[1, 3, 1]$;  $[1, 4, 1]$;  $[2, 3, 2]$;  $[2, 4, 2]$;  $[3, 4, 3]$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
