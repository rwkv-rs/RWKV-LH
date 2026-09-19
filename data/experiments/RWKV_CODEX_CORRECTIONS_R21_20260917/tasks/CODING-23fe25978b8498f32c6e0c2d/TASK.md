**Problem Description**  
Inspired by the ice sculptures in Harbin, participants from the Arctic University of Robots and Automata decided to hold their own ice and snow festival on campus after the programming competition. They plan to harvest ice blocks from a nearby lake when it freezes in winter. To monitor the thickness of the ice layer, they first divide the lake surface into a grid and then deploy a lightweight robot to measure the ice thickness on each grid cell. Within the grid, there are three special cells designated as "checkpoints," which correspond to the robot reaching the quarter, halfway, and three-quarters points of its journey. At these three special "checkpoints," the robot sends a corresponding progress report. To avoid unnecessary wear and scratches on the ice surface, which might affect subsequent use, the robot must start from the cell at the bottom-left corner with coordinates $(0, 0)$, traverse each cell exactly once, and then return to the cell located at $(0, 1)$. If multiple routes meet the requirements, the robot will use a different route each day. The robot can only move one cell at a time in the north, south, east, or west directions.  
Given the size of the grid and the positions of the three checkpoints, write a program to determine how many different checkpoint routes exist. For example, if the lake surface is divided into a $3 \times 6$ grid, and the three checkpoints in order of visit are $(2, 1), (2, 4),$ and $(0, 4)$, the robot must start from the $(0, 0)$ cell, pass through $18$ cells, and finally end at the $(0, 1)$ cell. The robot must pass through the $(2, 1)$ cell on the $4^{th} \, (= \left\lfloor \dfrac{18}{4} \right\rfloor)$ step, the $(2, 4)$ cell on the $9^{th} \, (= \left\lfloor \dfrac{18}{2} \right\rfloor)$ step, and the $(0, 4)$ cell on the $13^{th} \, (= \left\lfloor \dfrac{3 \times 18}{4} \right\rfloor)$ step. There are only two routes that meet the requirements, as shown in the diagram below.  
![UVA1098 Robots on Ice](https://cdn.luogu.com.cn/upload/image_hosting/vy6tphyl.png)  
Note: (1) When the grid's size is not a multiple of $4$, use floor division in step calculation; (2) There may be scenarios where no valid routes exist. For example, given a $4 \times 3$ grid with three checkpoints at $(2, 0), (3, 2),$ and $(0, 2)$, no route starts from the $(0, 0)$ cell, ends at the $(0, 1)$ cell, and meets the requirements.

**Input Format**  
**This problem contains multiple datasets.**  
Each dataset's first line contains two integers $m$ and $n \, (2 \leq m, n \leq 8)$, representing the number of rows and columns in the grid. The following line contains six integers $r_1, c_1, r_2, c_2, r_3, c_3$, where $0 \leq r_i < m, 0 \leq c_i < n \, (i=1, 2, 3)$. The input is terminated by a line containing two zeroes.

**Output Format**  
Starting from $1$, print the dataset number and the number of distinct routes: the number of routes in which the robot starts at row $0$, column $0$, finishes at row $0$, column $1$, and passes through row $r_i$ and column $c_i \, (i=1, 2, 3)$ at step $\left\lfloor \dfrac{i \times m \times n}{4} \right\rfloor$, traversing all grid cells exactly once.
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
