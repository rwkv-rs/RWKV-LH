This problem is interactive . We have hidden an array $a$ of $n$ pairwise different numbers (this means that no two numbers are equal). You can get some information about this array using a new device you just ordered on Amazon. This device can answer queries of the following form: in response to the positions of $k$ different elements of the array, it will return the position and value of the $m$-th among them in the ascending order. Unfortunately, the instruction for the device was lost during delivery. However, you remember $k$, but don't remember $m$. Your task is to find $m$ using queries to this device. You can ask not more than $n$ queries . Note that the array $a$ and number $m$ are fixed before the start of the interaction and don't depend on your queries. In other words, interactor is not adaptive . Note that you don't have to minimize the number of queries, and you don't need to guess array $a$. You just have to guess $m$.

## Time Limit and Memory Limit

Time Limit: 1 second
Memory Limit: 256 megabytes

## Input Specification

The first line contains two integers $n$ and $k$ ($1\le k < n \le 500$) — the length of the array and the number of the elements in the query. It is guaranteed that number $m$ satisfies $1\le m \le k$, elements $a_1, a_2, \dots, a_n$ of the array satisfy $0\le a_i \le 10^9$, and all of them are different.

## Output Specification

None

## Examples

### Input #1

4 3
4 9
4 9
4 9
1 2

### Output #1

? 2 3 4
? 1 3 4
? 1 2 4
? 1 2 3
! 3

## Note

In the example, $n = 4$, $k = 3$, $m = 3$, $a = [2, 0, 1, 9]$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
