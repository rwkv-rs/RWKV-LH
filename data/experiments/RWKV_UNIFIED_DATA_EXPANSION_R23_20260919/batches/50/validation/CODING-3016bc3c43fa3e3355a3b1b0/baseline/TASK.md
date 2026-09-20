Inna is fed up with jokes about female logic. So she started using binary logic instead. Inna has an array of n elements a 1 [1],  a 1 [2], ...,  a 1 [ n ] . Girl likes to train in her binary logic, so she does an exercise consisting of n stages: on the first stage Inna writes out all numbers from array a 1 , on the i -th ( i  ≥ 2) stage girl writes all elements of array a i , which consists of n  -  i  + 1 integers; the k -th integer of array a i is defined as follows: a i [ k ] =  a i  - 1 [ k ]  AND a i  - 1 [ k  + 1] . Here AND is bit-wise binary logical operation. Dima decided to check Inna's skill. He asks Inna to change array, perform the exercise and say the sum of all  elements she wrote out during the current exercise. Help Inna to answer the questions!

## Time Limit and Memory Limit

Time Limit: 3 seconds
Memory Limit: 256 megabytes

## Input Specification

The first line contains two integers n and m (1 ≤  n ,  m  ≤ 10 5 ) — size of array a 1 and number of Dima's questions. Next line contains n integers a 1 [1],  a 1 [2], ...,  a 1 [ n ] (0 ≤  a i  ≤ 10 5 ) — initial array elements. Each of next m lines contains two integers — Dima's question description. Each question consists of two integers p i ,  v i (1 ≤  p i  ≤  n ; 0 ≤  v i  ≤ 10 5 ) . For this question Inna should make a 1 [ p i ] equals v i , and then perform the exercise. Please, note that changes are saved from question to question.

## Output Specification

For each question print Inna's answer on a single line.

## Examples

### Input #1
3 4
1 1 1
1 1
2 2
3 2
1 2

### Output #1
6
4
7
12

## Note

None

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
