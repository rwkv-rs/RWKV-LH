There is an infinitely large triangular grid, as shown below. Each point with integer coordinates contains a lamp.

<image>

Initially, only the lamp at (X, 0) was on, and all other lamps were off. Then, Snuke performed the following operation zero or more times:

* Choose two integers x and y. Toggle (on to off, off to on) the following three lamps: (x, y), (x, y+1), (x+1, y).



After the operations, N lamps (x_1, y_1), \cdots, (x_N, y_N) are on, and all other lamps are off. Find X.

Constraints

* 1 \leq N \leq 10^5
* -10^{17} \leq x_i, y_i \leq 10^{17}
* (x_i, y_i) are pairwise distinct.
* The
input is consistent with the statement, and you can uniquely determine X.

Input

Input is given from Standard Input in the following format:


N
x_1 y_1
:
x_N y_N


Output

Print X.

Example

Input

4
-2 1
-2 2
0 1
1 0


Output

-1

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
