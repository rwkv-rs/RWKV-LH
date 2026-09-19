Little Lidia likes playing with numbers. Today she has a positive integer $n$, and she wants to decompose it into the product of positive integers.

Because Lidia is little, she likes to play with numbers with little difference. So, all numbers in the decomposition should differ by at most one. And of course, the product of all numbers in the decomposition must be equal to $n$. She considers two decompositions the same if and only if they have the same number of integers and there is a permutation that transforms the first one into the second one.

Write a program that finds all decompositions, which little Lidia can play with today.

## Input Format

The only line of the input contains a single integer $n (1 \le n \le 10^{18})$.

## Output Format

In the first line, output the number of decompositions of $n$, or $-1$ if this number is infinite. If the number of decompositions is finite, print all of them one per line. In each line, first print the number $k_i$ of elements in the decomposition. Then print $k_i$ integers in this decomposition in any order. Don't forget that decompositions which are different only in the order of elements are considered the same.

## Sample Input and Output

### Sample Input #1

```
12
```

### Sample Output #1

```
3
1 12
3 2 3 2
2 4 3
```

### Sample Input #2

```
1
```

### Sample Output #2

```
-1
```

## Notes

Time limit: 3 s, Memory limit: 512 MB.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
