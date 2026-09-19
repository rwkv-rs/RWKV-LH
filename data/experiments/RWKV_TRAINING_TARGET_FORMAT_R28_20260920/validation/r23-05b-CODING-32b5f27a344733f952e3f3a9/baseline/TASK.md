In a network with $N$ nodes connected by $N-1$ edges, each node is either a server or a client. If node $u$ is a client, it implies that among all nodes connected to $u$, there is exactly one server. Determine the minimum number of servers required to satisfy this condition.

## Input and Output Format

### Input Format

The input consists of multiple test cases. For each test case, the first line contains an integer $N(\le10000)$. 

The following $N-1$ lines each contain two integers $a_i, b_i$, indicating that there is a bidirectional edge connecting $a_i$ and $b_i$.

Each test case ends with a line containing a `0`, except for the last test case, which ends with a `-1`.

### Output Format

For each test case, output a single line representing the minimum number of servers needed.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
