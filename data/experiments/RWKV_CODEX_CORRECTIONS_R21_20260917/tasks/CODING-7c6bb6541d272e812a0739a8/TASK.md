### Problem Description

[PDF](https://uva.onlinejudge.org/external/10/p1073.pdf)

For a polygon with sides of arbitrary length and all parallel to the coordinate axes, we can describe it as follows: consider each of its internal angles. If an internal angle is $90^\circ$, it is represented by $\texttt R$; if it is $270^\circ$, it is represented by $\texttt O$. Starting from a certain point, read the $\texttt R$ and $\texttt O$ in a counter-clockwise order, resulting in a string composed of $\texttt R$ and $\texttt O$.

Clearly, a $\texttt R, \texttt O$ string can correspond to multiple polygons. For example, polygon $1$ in Figure $1$ can be described as $\texttt{RRRR}$, while polygon $2$ can be described as $\texttt{RRORRORRORRO}$, $\texttt{RORRORRORROR}$, or $\texttt{ORRORRORRORR}$.

Given an integer $L$, determine how many strings of length $L$ consisting of $\texttt R$ and $\texttt O$ can correspond to one or more polygons such that there is a point inside the polygon that can "see" all the internal angles of the polygon (that is, the lines from this point to all vertices of the polygon's internal angles do not intersect any sides of the polygon).

### Input Format

**There are multiple test cases within a single test point.**

For each test case, one line contains an integer $L (1 \leq L \leq 1,000)$.

The input ends with a line containing `0`.

### Output Format

For each test case, output the data point number and an integer representing the number of strings that meet the conditions mentioned above. The output format should strictly follow the sample output.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
