Grisha come to a contest and faced the following problem. You are given an array of size $n$, initially consisting of zeros. The elements of the array are enumerated from $1$ to $n$. You perform $q$ operations on the array. The $i$-th operation is described with three integers $l_i$, $r_i$ and $x_i$ ($1 \leq l_i \leq r_i \leq n$, $1 \leq x_i \leq n$) and means that you should add $x_i$ to each of the elements with indices $l_i, l_i + 1, \ldots, r_i$. After all operations you should find the maximum in the array. Grisha is clever, so he solved the problem quickly. However something went wrong inside his head and now he thinks of the following question: "consider we applied some subset of the operations to the array. What are the possible values of the maximum in the array?" Help Grisha, find all integers $y$ between $1$ and $n$ such that if you apply some subset (possibly empty) of the operations, then the maximum in the array becomes equal to $y$.

## Time Limit and Memory Limit

Time Limit: 2 seconds
Memory Limit: 256 megabytes

## Input Specification

The first line contains two integers $n$ and $q$ ($1 \leq n, q \leq 10^{4}$) — the length of the array and the number of queries in the initial problem. The following $q$ lines contain queries, one per line. The $i$-th of these lines contains three integers $l_i$, $r_i$ and $x_i$ ($1 \leq l_i \leq r_i \leq n$, $1 \leq x_i \leq n$), denoting a query of adding $x_i$ to the segment from $l_i$-th to $r_i$-th elements of the array, inclusive.

## Output Specification

In the first line print the only integer $k$, denoting the number of integers from $1$ to $n$, inclusive, that can be equal to the maximum in the array after applying some subset (possibly empty) of the given operations. In the next line print these $k$ integers from $1$ to $n$ — the possible values of the maximum. Print these integers in increasing order .

## Examples

### Input #1
4 3
1 3 1
2 4 2
3 4 4

### Output #1
4
1 2 3 4 

### Input #2
7 2
1 5 1
3 7 2

### Output #2
3
1 2 3 

### Input #3
10 3
1 1 2
1 1 3
1 1 6

### Output #3
6
2 3 5 6 8 9

## Note

Consider the first example. If you consider the subset only of the first query, the maximum is equal to $1$. If you take only the second query, the maximum equals to $2$. If you take the first two queries, the maximum becomes $3$. If you take only the fourth query, the maximum becomes $4$. If you take the fourth query and something more, the maximum becomes greater that $n$, so you shouldn't print it. In the second example you can take the first query to obtain $1$. You can take only the second query to obtain $2$. You can take all queries to obtain $3$. In the third example you can obtain the following maximums: You can achieve the maximim of $2$ by using queries: $(1)$.  You can achieve the maximim of $3$ by using queries: $(2)$.  You can achieve the maximim of $5$ by using queries: $(1, 2)$.  You can achieve the maximim of $6$ by using queries: $(3)$.  You can achieve the maximim of $8$ by using queries: $(1, 3)$.  You can achieve the maximim of $9$ by using queries: $(2, 3)$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
