Alice and Bob begin their day with a quick game. They first choose a starting number X 0  ≥ 3 and try to reach one million by the process described below. Alice goes first and then they take alternating turns. In the i -th turn, the player whose turn it is selects a prime number smaller than the current number, and announces the smallest multiple of this prime number that is not smaller than the current number. Formally, he or she selects a prime p  <  X i  - 1 and then finds the minimum X i  ≥  X i  - 1 such that p divides X i . Note that if the selected prime p already divides X i  - 1 , then the number does not change. Eve has witnessed the state of the game after two turns. Given X 2 , help her determine what is the smallest possible starting number X 0 . Note that the players don't necessarily play optimally. You should consider all possible game evolutions.

## Time Limit and Memory Limit

Time Limit: 1.5 seconds
Memory Limit: 256 megabytes

## Input Specification

The input contains a single integer X 2 ( 4 ≤  X 2  ≤ 10 6 ). It is guaranteed that the integer X 2 is composite, that is, is not prime.

## Output Specification

Output a single integer — the minimum possible X 0 .

## Examples

### Input #1
14

### Output #1
6

### Input #2
20

### Output #2
15

### Input #3
8192

### Output #3
8191

## Note

In the first test, the smallest possible starting number is X 0  = 6 . One possible course of the game is as follows:  Alice picks prime 5 and announces X 1  = 10 Bob picks prime 7 and announces X 2  = 14 . In the second case, let X 0  = 15 .  Alice picks prime 2 and announces X 1  = 16 Bob picks prime 5 and announces X 2  = 20 .

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
