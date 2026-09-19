There are multiple test cases, ending at $EOF$.

For each test case, you are given a string of length $N(N\leqslant3000)$. The task is to determine whether the brackets in the string are correctly matched. The matchable brackets are as follows:

$\{ ~~~~~~~  \}$

$[~~~~~~~~]$

$(~~~~~~~~)$

$<~~~~~~~>$

$(*~~~~*)$

### Note: $ (*$ and $*)$ should be regarded as a single bracket, not two separate ones.

If the brackets in the string are correctly matched, output $YES$. Otherwise, output $NO$ followed by the position of the first mismatched bracket.

## Input and Output Examples

### Input Example #1

```
(*a++(*)
(*a{+}*)
```

### Output Example #1

```
NO 6
YES
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
