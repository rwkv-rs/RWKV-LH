Shashank loves trees and math. He has a rooted tree, $\mathbf{T}$, consisting of $N$ nodes uniquely labeled with integers in the inclusive range $[1,N]$. The node labeled as $1$ is the root node of tree $\mathbf{T}$, and each node in $\mathbf{T}$ is associated with some positive integer value (all values are initially $\mbox{0}$). 

Let's define $\mathbf{F_k}$ as the $k^{th}$ Fibonacci number. Shashank wants to perform $2$ types of operations over his tree, $\mathbf{T}$:

$\mbox{U}$ $\mbox{X}$ $\boldsymbol{\mbox{k}}$

Update the subtree rooted at node $\mbox{X}$ such that the node at level $0$ in subtree $\mbox{X}$ (i.e., node $\mbox{X}$) will have $\mathbf{F_k}$ added to it, all the nodes at level $\mbox{I}$ will have $\boldsymbol{F}_{k+1}$ added to them, and so on. More formally, all the nodes at a distance $\mbox{D}$ from node $\mbox{X}$ in the subtree of node $\mbox{X}$ will have the $(k+D)^{\mathrm{th}}$ Fibonacci number added to them.
$Q$ $\mbox{X}$ $\mathbf{Y}$

Find the sum of all values associated with the nodes on the unique path from $\mbox{X}$ to $\mathbf{Y}$. Print your sum modulo $10^9+7$ on a new line.

Given the configuration for tree $\mathbf{T}$ and a list of $\mbox{M}$ operations, perform all the operations efficiently.

Note: $F_1=F_2=1$.

Input Format

The first line contains $2$ space-separated integers, $N$ (the number of nodes in tree $\mathbf{T}$) and $\mbox{M}$ (the number of operations to be processed), respectively. 

Each line $\boldsymbol{i}$ of the $N-1$ subsequent lines contains an integer, $\mbox{P}$, denoting the parent of the $(i+1)^{th}$ node. 

Each of the $\mbox{M}$ subsequent lines contains one of the two types of operations mentioned in the Problem Statement above.

Constraints

$1\leq N,M\leq10^5$
$1\leq X,Y\leq N$
$1\leq k\leq10^{15}$

Output Format

For each operation of type $2$ (i.e., $Q$), print the required answer modulo $10^9+7$ on a new line.

Sample Input
5 10
1
1
2
2
Q 1 5
U 1 1
Q 1 1
Q 1 2
Q 1 3
Q 1 4
Q 1 5
U 2 2
Q 2 3
Q 4 5

Sample Output
0
1
2
2
4
4
4
10

Explanation

Intially, the tree looks like this:

After update operation $1\:\:1$, it looks like this:

After update operation $\textbf{2}\:\textbf{2}$, it looks like this:

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
