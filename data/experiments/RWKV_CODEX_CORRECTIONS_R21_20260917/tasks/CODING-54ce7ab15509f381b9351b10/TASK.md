**Problem Overview**

In an n×m grid, there are empty spaces and obstacles, along with two "2"s and two "3"s. The task is to connect the two "2"s and the two "3"s with individual zigzag lines so that the total length is minimized (each line must pass through the center of each cell, with each unit square having a side length of 1).

The constraints are as follows: lines cannot pass through obstacle cells, and each empty cell can only contain one line. Thus, the two zigzag lines cannot intersect and neither line can intersect itself.

As illustrated, the total length of the zigzag lines is 18 (each of the cells containing "2" and "3" has a segment of length 0.5).  
**Input Format**

The input consists of multiple datasets. The first line of each dataset contains the positive integers n and m (1≤n, m≤9), followed by n lines, each containing m integers, describing the grid. 0 represents an empty cell, 1 represents an obstacle, 2 denotes a cell with a "2", and 3 denotes a cell with a "3".

**Output Format**

For each dataset, output a single line representing the minimum combined length of the two zigzag lines. If there is no solution, output 0.
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
