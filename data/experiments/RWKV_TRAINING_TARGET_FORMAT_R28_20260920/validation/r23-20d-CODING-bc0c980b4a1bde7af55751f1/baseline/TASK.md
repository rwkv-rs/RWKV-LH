A spell string consists of many spell characters, which can be represented by numbers. For example, spell characters $1,2$ can be combined to form a spell string $[1,2]$.

A non-empty substring of a spell string $S$ is called a generating spell of $S$.

For example, when $S=[1,2,1]$, its generating spells are $[1],[2],[1,2],[2,1],[1,2,1]$, totaling five. When $S=[1,1,1]$, its generating spells are $[1],[1,1],[1,1,1]$, totaling three. Initially, $S$ is an empty string.

A total of $n$ operations are performed, each adding a spell character to the end of $S$. After each operation, the number of generating spells of the current spell string $S$ needs to be calculated.

## Input Format

The first line contains an integer $n$.

The second line contains $n$ numbers, where the $i$-th number represents the spell character $x_i$ added in the $i$-th operation.

## Output Format

Output $n$ lines, each containing a number.
The $i$-th line's number represents the number of generating spells of $S$ after the $i$-th operation.

## Sample Input and Output

### Input Sample #1

```
7
1 2 3 3 3 1 2
```

### Output Sample #1

```
1
3
6
9
12
17
22
```

## Notes

### Data Size and Constraints
For $10\%$ of the data, $1 \le n \le 10$;
For $30\%$ of the data, $1 \le n \le 100$;
For $60\%$ of the data, $1 \le n \le 10^3$;
For $100\%$ of the data, $1 \le n \le 10^5$, $1 \leq x_i \leq 10^9$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
