One day in the IT lesson Anna and Maria learned about the lexicographic order. String x is lexicographically less than string y , if either x is a prefix of y (and x  ≠  y ), or there exists such i ( 1 ≤  i  ≤  min (| x |, | y |) ), that x i  <  y i , and for any j ( 1 ≤  j  <  i ) x j  =  y j . Here | a | denotes the length of the string a . The lexicographic comparison of strings is implemented by operator < in modern programming languages​​. The teacher gave Anna and Maria homework. She gave them a string of length n . They should write out all substrings of the given string, including the whole initial string, and the equal substrings (for example, one should write out the following substrings from the string " aab ": " a ", " a ", " aa ", " ab ", " aab ", " b "). The resulting strings should be sorted in the lexicographical order. The cunning teacher doesn't want to check all these strings. That's why she said to find only the k -th string from the list. Help Anna and Maria do the homework.

## Time Limit and Memory Limit

Time Limit: 2 seconds
Memory Limit: 256 megabytes

## Input Specification

The first line contains a non-empty string that only consists of small Latin letters (" a "-" z "), whose length does not exceed 10 5 . The second line contains the only integer k ( 1 ≤  k  ≤ 10 5 ).

## Output Specification

Print the string Anna and Maria need — the k -th (in the lexicographical order) substring of the given string. If the total number of substrings is less than k , print a string saying " No such line. " (without the quotes).

## Examples

### Input #1
aa
2

### Output #1
a

### Input #2
abc
5

### Output #2
bc

### Input #3
abab
7

### Output #3
b

## Note

In the second sample before string " bc " follow strings " a ", " ab ", " abc ", " b ".

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
