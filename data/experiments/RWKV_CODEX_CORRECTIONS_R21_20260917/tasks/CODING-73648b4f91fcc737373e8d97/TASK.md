#### Problem Summary

Write a program to detect exam cheating.

Cheating is defined as: correctly answering a leaked question of difficulty $d_1$, but incorrectly answering an un-leaked question of difficulty $d_2$, where $(d_1 > d_2)$.

#### Input Format

$T$ sets of data

For each set of data, the first line contains an integer $Q$, representing the number of questions;

The following $Q$ lines, each containing two numbers $d_i, s_i$ and a character $r_i$, represent the question difficulty, whether the question was leaked, and the response situation, respectively.

Where $1 \le d_i \le 10$, the larger the $d_i$, the more difficult the question;

$s_i \in \{0, 1\}$, where $0$ means un-leaked, and $1$ means leaked;

$r_i \in \{\texttt{i}, \texttt{c}\}$, where $\texttt{i}$ means answered correctly, and $\texttt{c}$ means answered incorrectly.

#### Output Format

An integer, representing the number of cheating questions.

#### Sample Input

```plain
2
4
2 0 i
3 1 c
4 1 c
5 1 i
4
2 0 i
4 1 c
3 0 i
5 1 c
```

#### Sample Output

```plain
2
4
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
