You have a password which you often type — a string $s$ of length $n$. Every character of this string is one of the first $m$ lowercase Latin letters. Since you spend a lot of time typing it, you want to buy a new keyboard. A keyboard is a permutation of the first $m$ Latin letters. For example, if $m = 3$, then there are six possible keyboards: abc , acb , bac , bca , cab and cba . Since you type your password with one finger, you need to spend time moving your finger from one password character to the next. The time to move from character $s_i$ to character $s_{i+1}$ is equal to the distance between these characters on keyboard. The total time you have to spend typing the password with a keyboard is called the slowness of this keyboard. More formaly, the slowness of keyboard is equal to $\sum\limits_{i=2}^{n} |pos_{s_{i-1}} - pos_{s_i} |$, where $pos_x$ is position of letter $x$ in keyboard. For example, if $s$ is aacabc and the keyboard is bac , then the total time of typing this password is $|pos_a - pos_a| + |pos_a - pos_c| + |pos_c - pos_a| + |pos_a - pos_b| + |pos_b - pos_c|$ = $|2 - 2| + |2 - 3| + |3 - 2| + |2 - 1| + |1 - 3|$ = $0 + 1 + 1 + 1 + 2 = 5$. Before buying a new keyboard you want to know the minimum possible slowness that the keyboard can have.

## Time Limit and Memory Limit

Time Limit: 1 second
Memory Limit: 256 megabytes

## Input Specification

The first line contains two integers $n$ and $m$ ($1 \le n \le 10^5, 1 \le m \le 20$). The second line contains the string $s$ consisting of $n$ characters. Each character is one of the first $m$ Latin letters (lowercase).

## Output Specification

Print one integer – the minimum slowness a keyboard can have.

## Examples

### Input #1

6 3
aacabc


### Output #1

5


### Input #2

6 4
aaaaaa


### Output #2

0


### Input #3

15 4
abacabadabacaba


### Output #3

16

## Note

The first test case is considered in the statement. In the second test case the slowness of any keyboard is $0$. In the third test case one of the most suitable keyboards is bacd .

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
