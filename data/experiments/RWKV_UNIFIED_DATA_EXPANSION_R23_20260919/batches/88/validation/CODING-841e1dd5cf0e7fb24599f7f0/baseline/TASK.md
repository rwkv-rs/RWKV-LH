**Problem Description:**

A large city wants to improve its public transportation system by adding sightseeing routes that pass through tourist attractions. Your task is to plan a bus route for the city's sightseeing buses.

You will be given a set of tourist attractions. For each given attraction, only one bus route can pass through, and the bus route can only pass through this attraction once. There can be an unlimited number of bus routes, but each route must contain at least two attractions.

The roads connecting two attractions are unidirectional. For the road (i, j), its length is d(i, j). Note that even if both (i, j) and (j, i) exist, d(i, j) and d(j, i) are not necessarily the same. Each bus route must be a directed cycle.

You need to find the minimum total length of the bus routes, which is the sum of d for all roads used by the bus routes.

**Input Format:**

Multiple sub-tasks. Each sub-task's first line is a positive integer n, indicating the number of attractions, labeled with numbers from 1 to n.

The next n lines, the i+1 line describes the unidirectional roads starting from i. The (2k-1)th number represents the endpoint j of one road, and the 2kth number represents d(i, j). Each line ends with a single '0'.

The input file ends with a line containing only a single '0'.

**Output Format:**

For each sub-task, output one line. If there are bus routes that meet the requirements, output the minimum total length of the bus routes. Otherwise, output the letter 'N'.
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
