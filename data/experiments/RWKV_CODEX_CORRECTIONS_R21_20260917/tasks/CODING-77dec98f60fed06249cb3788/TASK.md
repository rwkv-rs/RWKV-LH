There are $n$ **distinct** people and $n$ **distinct** problems.

The $i$-th person is happy if and only if they are assigned $i$ problems.

Find the number of assignment schemes where at least one person is happy.

## Input Format

A single positive integer: $n$.

## Output Format

A number: your answer modulo $10^9+7$.

## Sample Input and Output

### Sample Input #1

```
1
```

### Sample Output #1

```
1
```

### Sample Input #2

```
2
```

### Sample Output #2

```
3
```

### Sample Input #3

```
314
```

### Sample Output #3

```
192940893
```

## Notes

### Data Range

**This problem is a bundled test.**

- For $22$ points, $2 \leq n \leq 7$.
- For another $33$ points, $1 \leq n \leq 20$.
- For all data, $1 \leq n \leq 350$.

### Sample #2 Explanation

There are $3$ possible schemes:

- The first problem is assigned to the first person, and the second problem is assigned to the second person.
- The second problem is assigned to the first person, and the first problem is assigned to the second person.
- Both problems are assigned to the second person.

### Notes

**The problem is translated from [COCI2019-2020](https://hsin.hr/coci/archive/2019_2020/) [CONTEST #5](https://hsin.hr/coci/archive/2019_2020/contest5_tasks.pdf) _T5 Zapina_**, translated by [90693](/user/90693).

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
