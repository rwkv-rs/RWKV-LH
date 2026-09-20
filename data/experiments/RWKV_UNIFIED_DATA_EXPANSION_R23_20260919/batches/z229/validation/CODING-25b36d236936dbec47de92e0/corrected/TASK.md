Alice has a string consisting of characters ' A ', ' B ' and ' C '. Bob can use the following transitions on any substring of our string in any order any number of times: A BC B AC C AB AAA empty string Note that a substring is one or more consecutive characters. For given queries, determine whether it is possible to obtain the target string from source.

## Time Limit and Memory Limit

Time Limit: 2 seconds
Memory Limit: 256 megabytes

## Input Specification

The first line contains a string S ( 1 ≤ | S | ≤ 10 5 ). The second line contains a string T ( 1 ≤ | T | ≤ 10 5 ), each of these strings consists only of uppercase English letters ' A ', ' B ' and ' C '. The third line contains the number of queries Q ( 1 ≤  Q  ≤ 10 5 ). The following Q lines describe queries. The i -th of these lines contains four space separated integers a i , b i , c i , d i . These represent the i -th query: is it possible to create T [ c i .. d i ] from S [ a i .. b i ] by applying the above transitions finite amount of times? Here, U [ x .. y ] is a substring of U that begins at index x (indexed from 1) and ends at index y . In particular, U [1..| U |] is the whole string U . It is guaranteed that 1 ≤  a  ≤  b  ≤ | S | and 1 ≤  c  ≤  d  ≤ | T | .

## Output Specification

Print a string of Q characters, where the i -th character is ' 1 ' if the answer to the i -th query is positive, and ' 0 ' otherwise.

## Examples

### Input #1
AABCCBAAB
ABCB
5
1 3 1 2
2 2 2 4
7 9 1 1
3 4 2 3
4 5 1 3

### Output #1
10011

## Note

In the first query we can achieve the result, for instance, by using transitions . The third query asks for changing AAB to A  — but in this case we are not able to get rid of the character ' B '.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
