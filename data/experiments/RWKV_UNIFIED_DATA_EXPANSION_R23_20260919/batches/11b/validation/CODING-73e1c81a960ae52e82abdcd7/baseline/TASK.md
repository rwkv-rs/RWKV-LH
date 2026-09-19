Read a positive integer $n$ from the file ($10 \le n \le 31000$). The task is to partition $n$ into a sum of several positive integers such that the product of these integers is maximized.

For example, if $n=13$, then when $n$ is expressed as $4+3+3+3$ (or $2+2+3+3+3$), the product $=108$ is the maximum.

## Input Format

A single line containing a positive integer $n$.

## Output Format

The first line should output an integer representing the number of digits of the maximum product.

The second line should output the first 100 digits of the maximum product. If the product has fewer than 100 digits, output the actual number of digits of the product.

## Sample Input and Output

### Sample Input #1

```
13
```

### Sample Output #1

```
3
108
```

## Notes

### Data Range and Constraints

For all test cases, $10 \le n \le 31000$, and the number of digits of the maximum product does not exceed 5000 digits.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
