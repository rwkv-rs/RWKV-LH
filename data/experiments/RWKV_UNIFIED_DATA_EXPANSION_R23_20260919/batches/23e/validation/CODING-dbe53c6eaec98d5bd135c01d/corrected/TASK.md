Arkady's code contains $n$ variables. Each variable has a unique name consisting of lowercase English letters only. One day Arkady decided to shorten his code. He wants to replace each variable name with its non-empty prefix so that these new names are still unique (however, a new name of some variable can coincide with some old name of another or same variable). Among such possibilities he wants to find the way with the smallest possible total length of the new names. A string $a$ is a prefix of a string $b$ if you can delete some (possibly none) characters from the end of $b$ and obtain $a$. Please find this minimum possible total length of new names.

## Time Limit and Memory Limit

Time Limit: 1 second
Memory Limit: 256 megabytes

## Input Specification

The first line contains a single integer $n$ ($1 \le n \le 10^5$) — the number of variables. The next $n$ lines contain variable names, one per line. Each name is non-empty and contains only lowercase English letters. The total length of these strings is not greater than $10^5$. The variable names are distinct.

## Output Specification

Print a single integer — the minimum possible total length of new variable names.

## Examples

### Input #1
3
codeforces
codehorses
code

### Output #1
6

### Input #2
5
abba
abb
ab
aa
aacada

### Output #2
11

### Input #3
3
telegram
digital
resistance

### Output #3
3

## Note

In the first example one of the best options is to shorten the names in the given order as " cod ", " co ", " c ". In the second example we can shorten the last name to " aac " and the first name to " a " without changing the other names.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
