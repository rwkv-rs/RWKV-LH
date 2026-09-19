To enhance her intelligence, ZJY has started studying probability theory. One day, she pondered over a question: For a randomly generated rooted binary tree with $n$ nodes (all non-isomorphic shapes are equally likely), what is the expected number of leaf nodes?

The pseudocode for determining if two trees are isomorphic is as follows:

$$
\def\arraystretch{1.2}
    \begin{array}{ll}
    \hline
    \textbf{Algorithm 1}&\text{Check}(T1,T2) \\
    \hline
    1&\textbf{Require: }\text{ Two trees' nodes }T1,T2\\
    2&\qquad\textbf{if}\ \ T1=\text{null}\textbf{ or }T2=\text{null}\textbf{ then }\\
    3&\qquad\qquad\textbf{return}\ \ T1=\text{null}\textbf{ and }T2=\text{null}\\
    4&\qquad\textbf{else}\\
    5&\qquad\qquad\textbf{return}\ \text{Check}(T1\to\mathit{leftson},T2\to\mathit{leftson}) \\ 
    & \qquad\qquad\qquad \textbf{ and }\text{Check}(T1\to\mathit{rightson},T2\to\mathit{rightson})\\
    6&\qquad\textbf{endif}\\
    \hline
    \end{array} 
    $$

## Input Format

Input a positive integer $n$, representing the number of nodes in the rooted tree.

## Output Format

Output the expected number of leaf nodes in the tree, with an error less than $10^{-9}$.

## Sample Input and Output

### Sample Input #1

```
1
```

### Sample Output #1

```
1.000000000
```

### Sample Input #2

```
3
```

### Sample Output #2

```
1.200000000
```

## Notes

### Data Range

For $30\%$ of the data, $1 \le n \le 10$.

For $70\%$ of the data, $1 \le n \le 100$.

For $100\%$ of the data, $1 \le n \le 10^9$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
