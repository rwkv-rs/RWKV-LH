The problem involves multiple datasets, and for each dataset, you are given two asteroids, each represented as an $N$-sided polygon. The number of sides $N$ satisfies $3 \leq N \leq 10$. The endpoints of the asteroid are given as coordinates $(x_i, y_i)$, where $-10000 \leq x_i, y_i \leq 10000$. Each asteroid also has a velocity represented by $(v_x, v_y)$, where $-100 \leq v_x, v_y \leq 100$.

Your task is to determine the time at which the intersecting area of the two moving asteroids reaches its maximum. If the intersecting area reaches its maximum multiple times, output the earliest such time. If the maximum intersecting area is zero, meaning at most one intersection point exists, output the earliest time of intersection. If the asteroids cannot intersect at all, output `impossible`. A tolerance of within $10^{-3}$ is permitted for errors.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
