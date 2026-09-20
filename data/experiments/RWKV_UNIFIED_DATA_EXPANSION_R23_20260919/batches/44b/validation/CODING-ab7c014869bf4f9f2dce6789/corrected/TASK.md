Imagine you are a hacker who has infiltrated a network of $n$ computers (numbered $0, 1, 2, 3, \ldots, n-1$). There are $n$ types of services, and each computer is running all services. For each computer, you can choose a service and terminate it on that computer and all its adjacent computers (if some services are already stopped, they remain stopped). Your goal is to completely paralyze as many services as possible (meaning that no computer is running that service).

## Input Format

The input consists of multiple datasets. Each dataset starts with an integer $n(1\leq n\leq 16)$: followed by $n$ lines, each describing a computer's neighboring computers. Each of these lines begins with an integer $m$, the number of adjacent computers, followed by $m$ integers representing the indices of these computers. The input ends with a line where $n=0$.

## Output Format

For each dataset, output the number of completely paralyzed services.

## Sample Input

```
3
2 1 2
2 0 2
2 0 1
4
1 1
1 0
1 3
1 2
0
```

## Sample Output

```
Case 1: 3
Case 2: 2
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
