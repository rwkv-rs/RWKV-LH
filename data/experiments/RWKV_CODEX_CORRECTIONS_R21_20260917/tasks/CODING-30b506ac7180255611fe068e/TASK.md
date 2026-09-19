In this version, $1 \leq n \leq 2000$. The hard version of this challenge is not offered in the round for the second division. Let's define a correct bracket sequence and its depth as follow: An empty string is a correct bracket sequence with depth $0$.  If " s " is a correct bracket sequence with depth $d$ then " (s) " is a correct bracket sequence with depth $d + 1$.  If " s " and " t " are both correct bracket sequences then their concatenation " st " is a correct bracket sequence with depth equal to the maximum depth of $s$ and $t$. For a (not necessarily correct) bracket sequence $s$, we define its depth as the maximum depth of any correct bracket sequence induced by removing some characters from $s$ (possibly zero). For example: the bracket sequence $s = $" ())(()) " has depth $2$, because by removing the third character we obtain a correct bracket sequence " ()(()) " with depth $2$. Given a string $a$ consists of only characters ' ( ', ' ) ' and ' ? '. Consider all (not necessarily correct) bracket sequences obtained by replacing all characters ' ? ' in $a$ by either ' ( ' or ' ) '. Calculate the sum of all the depths of all these bracket sequences. As this number can be large, find it modulo $998244353$. Hacks in this problem in the first division can be done only if easy and hard versions of this problem was solved.

## Time Limit and Memory Limit

Time Limit: 2 seconds
Memory Limit: 256 megabytes

## Input Specification

The only line contains a non-empty string consist of only ' ( ', ' ) ' and ' ? '. The length of the string is at most $2000$.

## Output Specification

Print the answer modulo $998244353$ in a single line.

## Examples

### Input #1

??


### Output #1

1


### Input #2

(?(?))


### Output #2

9

## Note

In the first test case, we can obtain $4$ bracket sequences by replacing all characters ' ? ' with either ' ( ' or ' ) ': " (( ". Its depth is $0$;  " )) ". Its depth is $0$;  " )( ". Its depth is $0$;  " () ". Its depth is $1$. So, the answer is $1 = 0 + 0 + 0 + 1$. In the second test case, we can obtain $4$ bracket sequences by replacing all characters ' ? ' with either ' ( ' or ' ) ': " (((()) ". Its depth is $2$;  " ()())) ". Its depth is $2$;  " ((())) ". Its depth is $3$;  " ()(()) ". Its depth is $2$. So, the answer is $9 = 2 + 2 + 3 + 2$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
