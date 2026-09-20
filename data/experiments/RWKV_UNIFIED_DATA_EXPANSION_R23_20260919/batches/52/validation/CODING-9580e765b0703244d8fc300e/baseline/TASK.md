Given a tree-shaped social network containing $n$ individuals (numbered from $1$ to $n$). If a person receives a message on a certain day, he will pass the message to all his direct social contacts the next day.

There are $m$ queries. Each query assumes that person $x$ receives a message on day $0$, and you are asked to calculate the number of people who receive this message for the first time on day $k$ (excluding those who have received the message before day $k$). The queries are independent of each other.

## Input Format

**This problem contains multiple sets of test data.**

The first line contains an integer $T$, the number of test data sets.

For each set of test data:

The first line contains two numbers $n$ and $m$, representing the number of people in the tree-shaped social network and the number of queries, respectively.

The next $n - 1$ lines each contain two numbers $a$ and $b$, indicating that person $a$ and person $b$ have a direct social relationship. The input guarantees a tree-shaped social network.

The next $m$ lines each contain two numbers $x$ and $k$, as described in the problem statement.

## Output Format

For each set of test data: Output $m$ lines, each containing a number representing the answer to the query.

## Sample Input and Output

### Input Sample #1

```
1
4 2
1 2
2 3
3 4
1 1
2 2
```

### Output Sample #1

```
1
1
```

## Notes

**Sample Explanation**

For the first query, the only person who receives the message for the first time on the first day is person $2$.
For the second query, persons $1$ and $3$ receive the message for the first time on the first day, and person $4$ receives the message for the first time on the second day.

**Data Range and Constraints**

For test case $1$: $1 \le n, m \le 10$.  
For test case $2$: $1 \le n, m \le 100$.  
For test case $3$: $1 \le n, m \le 1000$.  
For test cases $4$ to $6$: $1 \le n, m \le 10^5, k \le 20$.  
For test cases $7$ to $10$: $1 \le n, m \le 10^5$.  
For all test cases: $1 \le T \le 5, 1 \le x \le n, 0 \le k < n$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
