You are given an integer m . Let M  = 2 m  - 1 . You are also given a set of n integers denoted as the set T . The integers will be provided in base 2 as n binary strings of length m . A set of integers S is called "good" if the following hold.  If , then .  If , then  All elements of S are less than or equal to M . Here,  and  refer to the bitwise XOR and bitwise AND operators, respectively. Count the number of good sets S , modulo 10 9  + 7 .

## Time Limit and Memory Limit

Time Limit: 2 seconds
Memory Limit: 256 megabytes

## Input Specification

The first line will contain two integers m and n ( 1 ≤  m  ≤ 1 000 , 1 ≤  n  ≤  min (2 m , 50) ). The next n lines will contain the elements of T . Each line will contain exactly m zeros and ones. Elements of T will be distinct.

## Output Specification

Print a single integer, the number of good sets modulo 10 9  + 7 .

## Examples

### Input #1
5 3
11010
00101
11000

### Output #1
4

### Input #2
30 2
010101010101010010101010101010
110110110110110011011011011011

### Output #2
860616440

## Note

An example of a valid set S is {00000, 00101, 00010, 00111, 11000, 11010, 11101, 11111}.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
