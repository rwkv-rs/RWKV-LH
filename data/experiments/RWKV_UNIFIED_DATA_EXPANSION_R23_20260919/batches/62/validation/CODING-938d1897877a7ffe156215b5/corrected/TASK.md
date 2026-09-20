Given a directed strongly connected graph with $n$ nodes and $r$ edges, and positive integers $s$ and $b$ such that $1 \le s \le b \le n-1$, the $(b+1)$-th node is designated as the headquarters. The cost for node $x$ to send a message to node $y$ is $dis(x, b+1) + dis(b+1, y)$.

The set of nodes $\{1, 2, \cdots, b\}$ needs to be partitioned into $s$ disjoint subsets $S_1, S_2, \cdots, S_s$. Within each subset, every pair of nodes will send messages to each other. The goal is to minimize the total cost.

### Data Range

$2 \le n \le 5000$, $1 \le s \le b \le n-1$, $1 \le r \le 50000$, edge weights are non-negative and do not exceed $10000$.

## Problem Description

The Innovative Consumer Products Company (ICPC) is planning a top-secret project consisting of $s$ subprojects. There are $b \ge s$ branches involved, and ICPC wants to assign each branch to one of the subprojects, forming $s$ disjoint groups, each responsible for a subproject.

At the end of each month, each branch sends a message to every other branch in its group. ICPC has a specific communication protocol. Each branch $i$ has a secret key $k_i$ known only to the branch and the headquarters. If branch $i$ wants to send a message to branch $j$, it encrypts the message with its key $k_i$, a courier delivers it to the headquarters, which decrypts it with $k_i$ and re-encrypts it with $k_j$, and then the courier delivers it to branch $j$, which decrypts it with $k_j$. For security reasons, a courier can carry only one message at a time.

Given a road network and the locations of branches and the headquarters, your task is to determine the minimum total distance that couriers need to travel to deliver all end-of-month messages, for all possible assignments of branches to subprojects.

## Input Format

The first line contains four integers $n$, $b$, $s$, and $r$, where $n$ ($2 \le n \le 5000$) is the number of intersections, $b$ ($1 \le b \le n-1$) is the number of branches, $s$ ($1 \le s \le b$) is the number of subprojects, and $r$ ($1 \le r \le 50000$) is the number of roads. Intersections are numbered from $1$ to $n$. Branches are at intersections $1$ to $b$, and the headquarters is at intersection $b + 1$. Each of the next $r$ lines contains three integers $u$, $v$, and $\ell$, indicating a one-way road from intersection $u$ to intersection $v$ ($1 \le u, v \le n$) of length $\ell$ ($0 \le \ell \le 10000$). No ordered pair $(u, v)$ appears more than once, and from any intersection, it is possible to reach every other intersection.

## Output Format

Display the minimum total distance that couriers will need to travel.

## Sample Input and Output

### Input Sample #1

```
5 4 2 10
5 2 1
2 5 1
3 5 5
4 5 0
1 5 1
2 3 1
3 2 5
2 4 5
2 1 1
3 4 2
```

### Output Sample #1

```
13
```

### Input Sample #2

```
5 4 2 10
5 2 1
2 5 1
3 5 5
4 5 10
1 5 1
2 3 1
3 2 5
2 4 5
2 1 1
3 4 2
```

### Output Sample #2

```
24
```

## Notes/Hints

Time limit: 2000 ms, Memory limit: 1048576 kB.

International Collegiate Programming Contest (ACM-ICPC) World Finals 2016

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
