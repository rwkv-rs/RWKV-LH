Adventurers Platypus and Qlatyqus are currently exploring dungeons scattered across a vast plain. They are embarking on an adventure that spans $N$ days, and each day, either Platypus or Qlatyqus will explore a dungeon located at a certain point. Specifically, on the $i$-th day $(1 \leq i \leq N)$, if $A_i$ is `P`, Platypus will explore the dungeon at coordinates $(X_i, Y_i)$, and if $A_i$ is `Q`, Qlatyqus will explore the dungeon at the same coordinates. Here, $X_i$ and $Y_i$ are integers.

To cover as much area as possible, they should cooperate as much as possible. The reward $S_i$ for the two of them at the end of the $i$-th day is determined as follows:

- Consider the midpoint operation between a point of a dungeon explored by Platypus up to the $i$-th day and a point of a dungeon explored by Qlatyqus up to the $i$-th day. Let the set of all such midpoints be $M$. The reward $S_i$ is the area of the smallest convex polygon that encompasses all points in $M$. If such a convex polygon can have an arbitrarily small area, $S_i$ is set to $0$.

Platypus and Qlatyqus want to calculate how much their reward is each day. Given the exploration information for their $N$ days, create a program that reports the reward $S_i$ for the two of them at the end of each day. Since the values to be determined are rational numbers, output them modulo $998244353$ as described in the notes.

Output Method: When outputting a rational number, first represent it as a fraction $\frac{p}{q}$, where $p$ and $q$ are integers, and $q$ is not divisible by $998244353$ (under the constraints of this problem, such a representation is always possible). Then, output the unique integer $r$ such that $0 \leq r < 998244353$ and $p \equiv qr \pmod{998244353}$.

## Input Format

The input is given from the standard input in the following format:

> $N$ $A_1$ $X_1$ $Y_1$ $\vdots$ $A_N$ $X_N$ $Y_N$

## Output Format

Output $N$ lines. The $i$-th line should contain the value of the reward $S_i$ at the end of the $i$-th day, output as described in the output method.

## Sample Input and Output

### Sample Input #1

```
5
P 0 1
Q 1 0
P 2 1
Q 1 2
Q 2 2
```

### Sample Output #1

```
0
0
0
1
748683266
```

### Sample Input #2

```
8
P 0 0
Q 0 0
P 0 998244352
Q 0 998244352
P 998244352 0
Q 998244352 0
P 998244352 998244352
Q 998244352 998244352
```

### Sample Output #2

```
0
0
0
0
623902721
499122177
124780545
1
```

## Notes/Hints

### Constraints

- $1 \leq N \leq 2 \times 10^5$
- $X_i, Y_i$ are integers satisfying $0 \leq X_i, Y_i < 998244353$ $(1 \leq i \leq N)$
- $A_i$ is either the character `P` or `Q`
- If $i \neq j$ and $A_i = A_j$, then $(X_i, Y_i) \neq (X_j, Y_j)$

### Sample Explanation 1

- On the 1st day, Platypus explores the dungeon at coordinates $(0,1)$. Since Qlatyqus has not explored any dungeons yet, the reward is $0$.
- On the 2nd day, Qlatyqus explores the dungeon at coordinates $(1,0)$. The midpoint between the dungeons explored on the 1st and 2nd days is $\left(\frac{1}{2},\frac{1}{2}\right)$, but a convex polygon encompassing a single point can be arbitrarily small, so the reward is still $0$.
- For similar reasons, the reward on the 3rd day is also $0$.
- On the 4th day, the set of midpoints $M$ and the smallest convex polygon encompassing $M$ are as shown in the figure. Thus, the reward is $1$.
- The final set of midpoints $M$ and the convex polygon on the last day are shown in the figure. Thus, the reward is $\frac{5}{4}$, taking care to output it as described in the output method.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
