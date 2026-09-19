There are $N$ tasks and $M$ types of machines. Each type of machine can be rented or purchased. Each task consists of several steps, and each step requires a specific type of machine to complete.

You need to maximize the profit.

## Input Format

The first line provides $N$ and $M$.

The following lines describe each task. For each task, the first line gives $x_i$ and $t_i$, representing the income of the task and the number of steps, respectively.

The next $t_i$ lines, each containing two integers $a_{ij}$ and $b_{ij}$, represent the required machine for the step and the rental cost of that machine for this task.

The last $M$ lines, each containing a positive integer, represent the purchase cost of each machine.

## Output Format

The maximum profit.

## Sample Input and Output

### Input Sample #1

```
2 3
100 2
1 30
2 20
100 2
1 40
3 80
50
80
110
```

### Output Sample #1

```
50
```

## Notes/Hints

For $100\%$ of the data, it is guaranteed that $1 \le N, M \le 1200$, $1 \le x_i \le 5000$, and $b_{ij}, y_i \le 20000$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
