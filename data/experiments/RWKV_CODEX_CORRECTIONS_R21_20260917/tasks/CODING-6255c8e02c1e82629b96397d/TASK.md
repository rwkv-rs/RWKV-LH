Welcome to the two-dimensional computational geometry problem $(110)_2$ in one~!

You need to write a program to answer the following queries.

**Please read the input and output formats carefully!**

### Query $(001)_2$: Find the Circumscribed Circle

- Input Format: `CircumscribedCircle` $x_1$ $y_1$ $x_2$ $y_2$ $x_3$ $y_3$

- Output Format: `(x,y,r)`, where $x,y$ describe the position of the center, and $r$ indicates the radius of the circle.

- Description: Given a triangle with vertices at $(x_1,y_1)$, $(x_2,y_2)$, $(x_3,y_3)$, find the center and radius of the triangle's circumscribed circle.

- Assumption: **The three points are not collinear.**

### Query $(010)_2$: Find the Inscribed Circle

- Input Format: `InscribedCircle` $x_1$ $y_1$ $x_2$ $y_2$ $x_3$ $y_3$

- Output Format: `(x,y,r)`, where $x,y$ describe the position of the center, and $r$ indicates the radius of the circle.

- Description: Given a triangle with vertices at $(x_1,y_1)$, $(x_2,y_2)$, $(x_3,y_3)$, find the center and radius of the triangle's inscribed circle.

- Assumption: **The three points are not collinear.**

### Query $(011)_2$: Find Tangent Line Through a Point

- Input Format: `TangentLineThroughPoint` $x_c$ $y_c$ $r$ $x_p$ $y_p$

- Output Format: `[angle1,angle2]` 
    - Output a list (similar to an array in Python) containing several (or $\boldsymbol{0}$) real numbers $\theta$, describing the angles of inclination of the tangent lines in degrees. **Note the unit is degrees, and you need to ensure that $\boldsymbol{\theta \in \left[0,180\right)}$**.

    - **Ensure the elements in the list are in ascending order.**

    - Output an empty list `[]` if no solution exists.

- Description: Given a circle $C$ with center $(x_c,y_c)$ and radius $r$, and a point $(x_p,y_p)$, find **all** lines passing through $P$ that are tangent to circle $C$.

### Query $(100)_2$: Find a Circle Through a Point and Tangent to a Line with Fixed Radius

- Input Format: `CircleThroughAPointAndTangentToALineWithRadius` $x_p$ $y_p$ $x_1$ $y_1$ $x_2$ $y_2$ $r$

- Output Format: `[(x1,y1),(x2,y2)]`

    - Output a list (similar to an array in Python) containing several (or $\boldsymbol{0}$) pairs $(x,y)$, describing the center of a circle.

    - **Ensure the elements in the list are sorted in ascending order by $x$ as the primary key and $y$ as the secondary key.**

    - Output an empty list `[]` if no solution exists.

- Description: Given a line $l$ passing through $(x_1,y_1)$ and $(x_2,y_2)$, a point $P(x_p,y_p)$, and a radius $r$. You need to find **all** circles $O$ that meet the following conditions:

    - $O$ is tangent to $l$.
    - Point $P$ is on circle $O$.
    - $O$ has a radius of $r$.

### Query $(101)_2$: Find a Circle Tangent to Two Lines with Fixed Radius

- Input Format: `CircleTangentToTwoLinesWithRadius` $x_1$ $y_1$ $x_2$ $y_2$ $x_3$ $y_3$ $x_4$ $y_4$ $r$

- Output Format: `[(x1,y1),(x2,y2)]`

    - Same as in query $(100)_2$.

    - Output a list (similar to an array in Python) containing several (or $\boldsymbol{0}$) pairs $(x,y)$, describing the center of a circle.

    - **Ensure the elements in the list are sorted in ascending order by $x$ as the primary key and $y$ as the secondary key.**

    - Output an empty list `[]` if no solution exists.

- Description: Given a line $l_1$ passing through $(x_1,y_1)$ and $(x_2,y_2)$, another line $l_2$ passing through $(x_3,y_3)$ and $(x_4,y_4)$, and a radius $r$. You need to find **all** circles $O$ that meet the following conditions:

    - $O$ is tangent to both $l_1$ and $l_2$.
    - $O$ has a radius of $r$.

- Assumption: **Ensure that $\boldsymbol{l_1}$ and $\boldsymbol{l_2}$ are not parallel.**

### Query $(110)_2$: Find the Common External Tangent Circle with Fixed Radius

- Input Format: `CircleTangentToTwoDisjointCirclesWithRadius` $x_1$ $y_1$ $r_1$ $x_2$ $y_2$ $r_2$ $r$

- Output Format: `[(x1,y1),(x2,y2)]`

    - Same as in query $(100)_2$.

    - Output a list (similar to an array in Python) containing several (or $\boldsymbol{0}$) pairs $(x,y)$, describing the center of a circle.

    - **Ensure the elements in the list are sorted in ascending order by $x$ as the primary key and $y$ as the secondary key.**

    - Output an empty list `[]` if no solution exists.

- Description: Given a circle $C_1$ with radius $r_1$ and center $(x_1,y_1)$, another circle $C_2$ with radius $r_2$ and center $(x_2,y_2)$, and a given radius $r$. You need to find **all** circles $O$ that meet the following conditions:

    - $O$ is externally tangent to both $C_1$ and $C_2$. This means $O$ should not enclose $C_1$ or $C_2$.

    - $O$ has a radius of $r$.

Please note:

- For outputs where list elements are real numbers, ensure the elements in the list are **in ascending order**.

- For outputs where list elements are pairs $(x,y)$, ensure these pairs are **sorted in ascending order by $x$ as the primary key and $y$ as the secondary key**.

- Print an empty list `[]` if no solution exists.

- **Your output should not contain spaces.**

- **Each number in your output should be rounded to 6 decimal places.**

## Input Format

There are multiple sets of data for this problem. The number of data sets will not exceed $10^3$.

Each line contains a query in the format described above. All input numbers are guaranteed to be integers with an absolute value no greater than $10^3$.

The data ends with EOF (End of File).

## Output Format

For each query, output the result in the format described above.

**Each number in your output should be rounded to 6 decimal places.**

**For each list, enclose it within square brackets `[]`; for each pair, enclose it within parentheses `()`. Your output should not contain spaces.**
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
