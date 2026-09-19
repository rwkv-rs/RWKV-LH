Given a string s , find the number of ways to split s to substrings such that if there are k substrings ( p 1 ,  p 2 ,  p 3 , ...,  p k ) in partition, then p i  =  p k  -  i  + 1 for all i (1 ≤  i  ≤  k ) and k is even. Since the number of ways can be large, print it modulo 10 9  + 7 .

## Time Limit and Memory Limit

Time Limit: 3 seconds
Memory Limit: 256 megabytes

## Input Specification

The only line of input contains a string s (2 ≤ | s | ≤ 10 6 ) of even length consisting of lowercase Latin letters.

## Output Specification

Print one integer, the number of ways of partitioning the string modulo 10 9  + 7 .

## Examples

### Input #1
abcdcdab

### Output #1
1

### Input #2
abbababababbab

### Output #2
3

## Note

In the first case, the only way to partition the string is ab | cd | cd | ab . In the second case, the string can be partitioned as ab | b | ab | ab | ab | ab | b | ab or ab | b | abab | abab | b | ab or abbab | ab | ab | abbab .

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
