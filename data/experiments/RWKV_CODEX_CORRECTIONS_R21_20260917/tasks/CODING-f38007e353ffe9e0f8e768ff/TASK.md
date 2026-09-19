Alice and Bob want to play a game. They have $n$ colored paper strips; the $i$-th strip is divided into $a_i$ cells numbered from $1$ to $a_i$. Each cell can have one of $3$ colors. In the beginning of the game, Alice and Bob put $n$ chips, the $i$-th chip is put in the $a_i$-th cell of the $i$-th strip. Then they take turns, Alice is first. Each player during their turn has to choose one chip and move it $1$, $2$ or $3$ cells backwards (i. e. if the current cell is $x$, then the chip can be moved to the cell $x - 1$, $x - 2$ or $x - 3$). There are two restrictions: the chip cannot leave the borders of the strip (for example, if the current cell is $3$, then you can't move the chip $3$ cells backwards); and some moves may be prohibited because of color of the current cell (a matrix $f$ with size $3 \times 3$ is given, where $f_{i, j} = 1$ if it is possible to move the chip $j$ cells backwards from the cell which has color $i$, or $f_{i, j} = 0$ if such move is prohibited). The player who cannot make a move loses the game. Initially some cells may be uncolored. Bob can color all uncolored cells as he wants (but he cannot leave any cell uncolored). Let's call a coloring good if Bob can win the game no matter how Alice acts, if the cells are colored according to this coloring. Two colorings are different if at least one cell is colored in different colors in these two colorings. Bob wants you to calculate the number of good colorings. Can you do it for him? Since the answer can be really large, you have to print it modulo $998244353$.

## Time Limit and Memory Limit

Time Limit: 5 seconds
Memory Limit: 512 megabytes

## Input Specification

The first line contains one integer $n$ — the number of paper strips ($1 \le n \le 1000$). The second line contains $n$ integers $a_1$, $a_2$, ..., $a_n$ ($1 \le a_i \le 10^9$), where $a_i$ is the number of cells in the $i$-th strip. The third line contains one integer $m$ ($1 \le m \le 1000$) — the number of cells that are already colored. Then $m$ lines follow, each describing an already colored cell. The $i$-th of these lines contains three integers $x_i$, $y_i$ and $c_i$ ($1 \le x_i \le n$, $1 \le y_i \le a_{x_i}$, $1 \le c_i \le 3$) denoting that the cell $y_i$ in the strip $x_i$ has color $c_i$. It is guaranteed that if $i \ne j$, then either $x_i \ne x_j$ or $y_i \ne y_j$ (or both). Then $3$ lines follow, $i$-th line containing $3$ numbers $f_{i, 1}$, $f_{i, 2}$, $f_{i, 3}$ ($0 \le f_{i, j} \le 1$). If $f_{i, j} = 1$, then it is possible to move the chip $j$ cells backwards from the cell having color $i$; if $f_{i, j} = 0$, then such move is impossible.

## Output Specification

Print one integer: the number of good colorings, taken modulo $998244353$.

## Examples

### Input #1

3
3 4 5
2
1 1 1
2 2 2
1 1 1
1 0 0
0 1 1


### Output #1

14346


### Input #2

1
1
1
1 1 1
1 1 1
1 1 1
1 1 1


### Output #2

1


### Input #3

3
1 1 1
1
1 1 1
1 1 1
1 1 1
1 1 1


### Output #3

9

## Note

None

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
