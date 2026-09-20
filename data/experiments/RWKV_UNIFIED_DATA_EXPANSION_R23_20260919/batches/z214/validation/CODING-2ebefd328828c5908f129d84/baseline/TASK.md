You need to assign serial numbers to a batch of products, where each serial number is a 7-digit hexadecimal number (consisting of digits from 0 to 9 and letters from a to f).

To prevent errors during manual processing, it is required that any two serial numbers differ in at least three positions.

The first serial number is 0000000, the second serial number is the smallest number that does not violate the above rule, and so on. Each time a new serial number is assigned, it is always the smallest number that does not conflict with the previous ones (note that serial numbers are hexadecimal and can be compared in size).

Following this rule, the first few serial numbers are:

$$0000000, 0000111, 0000222, \ldots, 0000fff, 0001012, 0001103, 0001230, 0001321, 0001456, \ldots$$

Given an integer \( k \), your task is to find the \( k \)-th smallest serial number.

## Input Format

A single line containing an integer \( k \).

## Output Format

Output the \( k \)-th smallest serial number (all letters should be lowercase). The input guarantees that this serial number exists.

## Sample Input and Output

### Sample Input #1

```
20
```

### Sample Output #1

```
0001321
```

## Notes/Hints

For 15% of the data, \( k \leq 200 \);

For 35% of the data, \( k \leq 10000 \);

For 60% of the data, \( k \leq 200000 \);

For 100% of the data, \( k \leq 1048576 \).

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
