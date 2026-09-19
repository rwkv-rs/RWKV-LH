There are $n$ people who criticize each other.

A matrix $A$ is also provided.

The rules are as follows:

- For the first time, the 1st person criticizes the 2nd person.

- If the $(i-1)$-th time is the $u$-th person criticizing the $v$-th person,

  then the $i$-th time is the $v$-th person criticizing the $A_{v,u}$-th person.

Determine who **conducts** the criticism (note: not **receives** the criticism) on the $k$-th occasion.

## Input Format

The first line contains two positive integers, $n$ and $k$.

The following $n$ lines represent the matrix $A$. The main diagonal (the diagonal from the top-left to the bottom-right) consists of all $0$s, and the other parts are composed of positive integers from $1$ to $n$.

## Output Format

A single line containing your answer.

## Sample Input and Output

### Sample Input #1

```
2 4
0 2
1 0
```

### Sample Output #1

```
2
```

### Sample Input #2

```
3 7
0 3 2
3 0 3
2 1 0
```

### Sample Output #2

```
1
```

### Sample Input #3

```
4 7
0 4 3 2
4 0 4 1
2 1 0 1
3 2 3 0
```

### Sample Output #3

```
3
```

## Notes

### Data Range

- For $35$ points, it is guaranteed that $1 \leq k \leq 10^5$.
- For all data, $2 \leq n \leq 500$ and $1 \leq k \leq 10^{18}$.

### Notes

**The problem was translated from [COCI2019-2020](https://hsin.hr/coci/archive/2019_2020/) [CONTEST #5](https://hsin.hr/coci/archive/2019_2020/contest5_tasks.pdf) _T2 Političari_**, translated by [90693](/user/90693).

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
