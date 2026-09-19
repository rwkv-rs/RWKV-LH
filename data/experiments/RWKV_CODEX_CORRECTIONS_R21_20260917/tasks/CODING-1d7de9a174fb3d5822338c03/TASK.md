For a long time, you have been a loyal fan of Bytelotto, but your family always tells you that all such games are a waste of money. You believe this is definitely because they lack skills. You have a great plan, and everyone will soon see you winning the game.

There are many types of games, and you are interested in one of them: Bitlotto. The rules are simple; a number is randomly drawn every day as the winning number. You have noted down the winning numbers for $n$ consecutive days: $a_1, a_2, \ldots, a_n$. You are convinced that there is a pattern, especially within consecutive intervals of $l$ days. Your family still doesn't believe you, so the only way to convince them is through reliable mathematics.

There are $n-l+1$ intervals of length $l$. The $i$-th interval starts at $i$ and thus contains the elements $a_i, a_{i+1}, \ldots, a_{i+l-1}$. The distance between two intervals is defined as the number of positions where the corresponding numbers are not equal. Formally, the distance between the $x$-th interval and the $y$-th interval is the number of positions $i$ (where $0 \le i < l$) such that $a_{x+i} \ne a_{y+i}$. We define two intervals as $k$-similar if and only if the distance between them is at most $k$.

Given the winning numbers for $n$ consecutive days and $q$ queries, for each query, you are given an integer $k_j$, and you need to find, for each interval of length $l$ in the sequence, the number of intervals that are $k_j$-similar to it (excluding itself).

## Input Format

The first line of standard input contains two integers $n$ and $l$, representing the number of days and the length of the interval you need to analyze, respectively.

The second line contains $n$ space-separated integers $a_1, a_2, \ldots, a_n$, where $a_i$ represents the winning number on the $i$-th day.

The third line contains an integer $q$, representing the number of queries.

The next $q$ lines each contain an integer $k_j$, representing the similarity parameter for the $j$-th query.

## Output Format

Output $q$ lines, with the $j$-th line containing $n-l+1$ space-separated integers, representing the answers for the $j$-th query. The $i$-th number in a line represents the number of intervals that are $k_j$-similar to the $i$-th interval, excluding itself.

## Sample Input and Output

### Input Sample #1

```
6 2
1 2 1 3 2 1
2
1
2
```

### Output Sample #1

```
2 1 1 1 1
4 4 4 4 4
```

## Notes/Hints

### Sample Explanation

The sequence has five intervals of length $2$:

- The first interval contains $1$ $2$;
- The second interval contains $2$ $1$;
- The third interval contains $1$ $3$;
- The fourth interval contains $3$ $2$;
- The fifth interval contains $2$ $1$.

There are two queries.

For the first query with $k=1$, the first and third intervals—$1$ $2$ and $1$ $3$—differ only at the second position, so their distance is $1$. Similarly, the first and fourth intervals—$1$ $2$ and $3$ $2$—differ only at the first position, so their distance is $1$. Only these two intervals are $1$-similar to the first interval, so the first number output is $2$.

For the second query with $k=2$, all intervals are $2$-similar.

### Data Size and Constraints

For $100\%$ of the data, $1 \le n \le 10^4$, $1 \le a_i \le 10^9$, $1 \le q \le 100$, $0 \le k_j \le l$.

The test data is divided into several subtasks with additional constraints, each containing several test cases.

| Subtask | Additional Constraints | Score |
| :-----: | :--------------------: | :---: |
|    $1$  |       $n \le 300$      |  $25$ |
|    $2$  |      $n \le 2000$      |  $20$ |
|    $3$  |      $q=1, k_1=0$      |  $20$ |
|    $4$  |         $q=1$          |  $15$ |
|    $5$  |     No additional constraints     |  $20$ |

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
