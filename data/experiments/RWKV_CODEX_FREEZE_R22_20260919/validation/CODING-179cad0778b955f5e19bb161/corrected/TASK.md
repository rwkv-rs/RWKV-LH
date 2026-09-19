NOIP2017 Junior Group T2

## Problem Description

Each book in the library has a unique book code, which is a positive integer used for quick retrieval. Each reader has a demand code, which is also a positive integer. If a book's code ends with a reader's demand code, then that book is what the reader needs. Xiao D has just become a librarian and knows the book codes of all the books in the library. She asks you to write a program that, for each reader, finds the book with the smallest book code that matches their demand code. If no such book exists, output `-1`.

## Input Format

The first line contains two positive integers $n$ and $q$, separated by a space, representing the number of books in the library and the number of readers, respectively.

The next $n$ lines each contain a positive integer representing the book code of a book in the library.

The next $q$ lines each contain two positive integers separated by a space. The first integer represents the length of the reader's demand code, and the second integer represents the reader's demand code.

## Output Format

$q$ lines, each containing an integer. If the $i$-th reader's book is found, output the smallest book code of the books that match the $i$-th reader's demand code. Otherwise, output `-1`.

## Sample Input and Output

### Input Sample #1

```
5 5 
2123 
1123 
23 
24 
24 
2 23 
3 123 
3 124 
2 12 
2 12
```

### Output Sample #1

```
23 
1123 
-1 
-1 
-1 
```

## Notes

**Data Size and Constraints**

For $20\%$ of the data, $1 ≤ n ≤ 2$.

For another $20\%$ of the data, $q = 1$.

For another $20\%$ of the data, all reader demand codes have a length of $1$.

For another $20\%$ of the data, all book codes are given in ascending order.

For $100\%$ of the data, $1 ≤ n ≤ 1000, 1 ≤ q ≤ 1000$, and all book codes and demand codes do not exceed $10^7$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
