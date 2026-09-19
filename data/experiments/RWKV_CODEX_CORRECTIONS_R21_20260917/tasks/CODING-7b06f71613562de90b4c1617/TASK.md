Qiangqiang and Mengmeng are good friends. One day, while they were wandering outside, they suddenly saw a Bauhinia tree ahead. It was the season when Bauhinia blossoms were fluttering, and countless petals were visibly growing from the Bauhinia tree.

Upon closer inspection, this large tree is actually a weighted tree. At each moment, it grows a new leaf node, and each node has a cute little elf. A new elf also appears on the newly grown node. Elves are adorable but also fragile creatures. Each elf $i$ has a sensitivity value $r_i$. Elves $i$ and $j$ become friends if and only if the distance $dist(i,j) \leq r_i + r_j$ on the tree, where $dist(i,j)$ represents the sum of the weights of all edges on the unique path from $i$ to $j$ on the tree.

Qiangqiang and Mengmeng are curious about how many pairs of friends there are on the tree each time a new leaf node is added.

We assume the tree is initially empty, and nodes are numbered sequentially starting from 1 as they are added. Since Qiangqiang is very curious, you must immediately provide the total number of friend pairs after each new node appears, without delay.

## Input Format

The first line contains an integer representing the test point number.

The second line contains a positive integer $n$, indicating the total number of nodes to be added.

Let the total number of friend pairs before adding a node be $last\_ans$, which is initially 0.

The next $n$ lines, the $i$-th line contains three non-negative integers $a_i, c_i, r_i$, indicating that the parent node of node $i$ is numbered as $a_i \oplus (last\_ans \mod 10^9)$ (where $\oplus$ denotes the XOR operation, and the data guarantees that the result is between 1 and $i-1$), the edge weight to the parent node is $c_i$, and the sensitivity value of the elf on node $i$ is $r_i$.

Note that $a_1 = c_1 = 0$, indicating that node 1 is the root node. For $i > 1$, the parent node number is at least 1.

## Output Format

Contains $n$ lines, each line outputs an integer, representing the number of friend pairs on the tree after adding the $i$-th node.

## Sample Input and Output

### Input Sample #1

```
0
5
0 0 6
1 2 4
0 9 4
0 5 5
0 2 4
```

### Output Sample #1

```
0
1
2
4
7
```

## Notes

All data satisfies $1 \leq c_i \leq 10^4$, $a_i \leq 2 \times 10^9$, $r_i \leq 10^9$.

| Test Point Number | Constraints                                                         |
| :----------------: | :------------------------------------------------------------------: |
| $1,2$              | $n \leq 100$                                                        |
| $3,4$              | $n \leq 1000$                                                       |
| $5,6,7,8$          | $n \leq 10^5$, node 1 has at most two children, other nodes have at most one child |
| $9,10$             | $n \leq 10^5$, $r_i \leq 10$                                        |
| $11,12$            | $n \leq 10^5$, the tree is randomly generated                       |
| $13,14,15$         | $n \leq 7 \times 10^4$                                              |
| $16,17,18,19,20$   | $n \leq 10^5$                                                       |

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
