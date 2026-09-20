You are given a matrix f with 4 rows and n columns. Each element of the matrix is either an asterisk ( * ) or a dot ( . ). You may perform the following operation arbitrary number of times: choose a square submatrix of f with size k  ×  k (where 1 ≤  k  ≤ 4 ) and replace each element of the chosen submatrix with a dot. Choosing a submatrix of size k  ×  k costs a k coins. What is the minimum number of coins you have to pay to replace all asterisks with dots?

## Time Limit and Memory Limit

Time Limit: 1 second
Memory Limit: 256 megabytes

## Input Specification

The first line contains one integer n ( 4 ≤  n  ≤ 1000 ) — the number of columns in f . The second line contains 4 integers a 1 , a 2 , a 3 , a 4 ( 1 ≤  a i  ≤ 1000 ) — the cost to replace the square submatrix of size 1 × 1 , 2 × 2 , 3 × 3 or 4 × 4 , respectively. Then four lines follow, each containing n characters and denoting a row of matrix f . Each character is either a dot or an asterisk.

## Output Specification

Print one integer — the minimum number of coins to replace all asterisks with dots.

## Examples

### Input #1
4
1 10 8 20
***.
***.
***.
...*

### Output #1
9

### Input #2
7
2 1 8 2
.***...
.***..*
.***...
....*..

### Output #2
3

### Input #3
4
10 10 1 10
***.
*..*
*..*
.***

### Output #3
2

## Note

In the first example you can spend 8 coins to replace the submatrix 3 × 3 in the top-left corner, and 1 coin to replace the 1 × 1 submatrix in the bottom-right corner. In the second example the best option is to replace the 4 × 4 submatrix containing columns 2 – 5 , and the 2 × 2 submatrix consisting of rows 2 – 3 and columns 6 – 7 . In the third example you can select submatrix 3 × 3 in the top-left corner and then submatrix 3 × 3 consisting of rows 2 – 4 and columns 2 – 4 .

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
