You are given a binary string s (each character of this string is either 0 or 1 ). Let's denote the cost of string t as the number of occurences of s in t . For example, if s is 11 and t is 111011 , then the cost of t is 3 . Let's also denote the Fibonacci strings sequence as follows: F (0) is 0 ; F (1) is 1 ; F ( i ) =  F ( i  - 1) +  F ( i  - 2) if i  > 1 , where  +  means the concatenation of two strings. Your task is to calculate the sum of costs of all subsequences of the string F ( x ) . Since answer may be large, calculate it modulo 10 9  + 7 .

## Time Limit and Memory Limit

Time Limit: 3.5 seconds
Memory Limit: 256 megabytes

## Input Specification

The first line contains two integers n and x ( 1 ≤  n  ≤ 100 , 0 ≤  x  ≤ 100 ) — the length of s and the index of a Fibonacci string you are interested in, respectively. The second line contains s — a string consisting of n characters. Each of these characters is either 0 or 1 .

## Output Specification

Print the only integer — the sum of costs of all subsequences of the string F ( x ) , taken modulo 10 9  + 7 .

## Examples

### Input #1
2 4
11

### Output #1
14

### Input #2
10 100
1010101010

### Output #2
553403224

## Note

None

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
