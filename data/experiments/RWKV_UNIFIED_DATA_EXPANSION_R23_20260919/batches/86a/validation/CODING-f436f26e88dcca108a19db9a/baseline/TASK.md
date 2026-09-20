Xiao X is not very good at programming and has many problems that she has gotten wrong (WA). She feels very upset about this. Xiao Z decides to comfort her, but he has no WAs in his submission history (flag). Therefore, he decides to alter the attribution of half of the problems so that Xiao X will feel better seeing that they have made similar mistakes.

## Problem Description

Each WA problem has a score. Xiao X has a method to judge whether the WA problems of two people are similar:

She came up with a magical function:

$$f(x)=a_1x^0+a_2x^1+a_3x^2+\cdots+a_{n}x^{n-1}$$

She believes that if the sums of two sets of $f(x)$ are equal for any values of $a_i$, then the error levels of the two sets of problems are similar.

For example, if there are two sets of WA problems with scores $A=\{1,4,6,7 \}$ and $B=\{2,3,5,8\}$, and when $a_1=a_2=a_3=1$, the magical function is:

$$f(x)=x^2+x+1$$

Then, $f(1)=3, f(2)=7, f(3)=13, \cdots$

Clearly: $f(1) + f(4) + f(6) + f(7) = 124 = f(2) + f(3) + f(5) + f(8)$.

For this set of coefficients, this grouping scheme is valid. It can be proven that for any values of $a_i$, the grouping scheme satisfies the condition (the sums of $f(x)$ for both groups are the same).

Therefore, $A=\{1,4,6,7 \}, B=\{2,3,5,8\}$ is a valid grouping.

## Input Format

The first line contains an integer $n$, representing that there are $2^n$ WA problems with scores ranging from $1$ to $2^n$, and $n \ge 2$.

The second line contains an integer $q$, indicating there are $q$ queries.

The last line contains $q$ integers, querying whose name is on the WA problem with score $x$.

(Since Xiao X is not very good, we assume that the WA problem with score $1$ is hers.)

## Output Format

There are $q$ lines in total. Each line contains a character 'X' or 'Z', indicating whose name is on the WA problem with score $x$.

## Sample Input and Output

### Sample Input #1

```
3
2
4 5
```

### Sample Output #1

```
X
Z
```

## Notes/Hints

### Data Range and Constraints

- For $10\%$ of the data, $2 \le n \le 4$, $q \le 10$;
- For $40\%$ of the data, $2 \le n \le 20$, $1 \le q \le 5000$;
- For $100\%$ of the data, $2 \le n \le 60$, $q \le 10^6$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
