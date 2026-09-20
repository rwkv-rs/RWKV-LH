Lies~ How could Stalin be in Hebei?

But... what if Stalin threw himself like a bomb into the bunker garden?

With this small hope, Leader Adolf walked into the garden alone. One day, we will meet again, Stalin. Maybe here, maybe in a distant place.

In any case, before that, let's decorate the garden nicely and choreograph a beautiful dance!

## Problem Description

The Leader divided the garden into a grid of $n$ rows and $m$ columns. Each cell can be marked to point in one of the four directions: up, down, left, or right. When the Leader is in a cell, he will move according to the direction indicated by the marker to an adjacent cell or exit the garden (i.e., the destination cell is outside the grid). For example, with the following arrangement, starting from the cell at the 3rd row and 2nd column, the Leader will exit the garden along the path marked in red; starting from the 2nd row and 22nd column, he will endlessly walk in the loop marked in blue.

![Example Image](https://cdn.luogu.com.cn/upload/pic/12659.png)

The Leader has already designed markers for most cells. He uses the characters L, R, U, D to represent markers pointing left, right, up, and down, respectively, and the character '.' to represent undecided cells. Now, the Leader hopes to replace each '.' with one of L, R, U, D, such that starting from any cell in the garden, following the rules, the Leader will eventually exit the garden.

You need to write a program to help the Leader calculate the number of different replacement schemes. Two schemes are considered different if and only if there exists a cell where the markers in the two schemes differ. Since the answer may be very large, output the number of schemes modulo $10^9 + 7$.

## Input Format

Read from standard input.

The first line contains a positive integer $T$ — the number of test cases. Following are $T$ test cases, formatted as follows, with no empty lines between test cases.

The first line of each test case: Two space-separated positive integers $n$ and $m$ — the number of rows and columns into which the garden is divided, respectively.

Next $n$ lines: Each line is a string of length $m$ consisting of characters L, R, U, D, and '.' — representing the pre-determined state of the garden cells.

## Output Format

Output to standard output.

For each test case, output one line — the number of valid schemes modulo $10^9 + 7$.

## Sample Input and Output

### Input Sample #1

```
5
3 9
LLRRUDUUU
LLR.UDUUU
LLRRUDUUU
4 4
LLRR
L.LL
RR.R
LLRR
4 3
LRD
LUL
DLU
RDL
1 2
LR
2 2
..
..
```

### Output Sample #1

```
3
8
0
1
192
```

## Notes/Hints

**Sample Explanation**

In the first set of data, replacing the only '.' with R, U, or D satisfies the requirement.

In the second set of data, replacing the two '.' in the top-left and bottom-right corners with any combination of LR, LU, LD, UR, UU, UD, DR, or DD satisfies the requirement.

In the third set of data, there are no undecided cells, and the original arrangement would cause the Leader to be stuck in an endless loop, so the answer is $0$. This set of data is the same as the example in the **Problem Description**.

In the fourth set of data, there are also no undecided cells, but the original arrangement already satisfies the requirement, so the answer is $1$.

Let $k$ denote the total number of cells marked as undecided (i.e., containing '.').

For all data, $1 \leq T \leq 10$, $1 \leq n, m \leq 200$, $0 \leq k \leq \min(nm, 300)$.

![Explanation Image](https://cdn.luogu.com.cn/upload/pic/12660.png)

"... wie Stalin!"

The problem statement is unrelated to historical facts.

From CodePlus December 2017, hosted by the Student Algorithm and Competition Association of the Department of Computer Science and Technology, Tsinghua University.

Credit: Idea/Lv Shiqing, Problem Setting/Lv Shiqing, Problem Verification/Wang Yuzhong, Yang Jingqin

Git Repo: https://git.thusaac.org/publish/CodePlus201712

Thanks to Tencent for supporting this competition.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
