In brief, this problem involves conversion between base-26 and decimal systems. Where 'a' corresponds to 1 and 'z' corresponds to 26. You are required to write a program to perform conversions between base-26 and decimal.

Input
The input can be in base-26 or decimal. When the input is '*', the input is terminated.

Output
For each word or number from the input data, output a line. This line should start with the word, followed by the appropriate number of spaces, and from the 23rd column onward, the corresponding numerical representation. Numbers exceeding three digits should be separated by commas, breaking into thousands, millions, etc.

## Example Input/Output

### Sample Input #1

```
29697684282993
transcendental
28011622636823854456520
computationally
zzzzzzzzzzzzzzzzzzzz
*
```

### Sample Output #1

```
elementary
transcendental
prestidigitation
computationally
zzzzzzzzzzzzzzzzzzzz
29,697,684,282,993
51,346,529,199,396,181,750
28,011,622,636,823,854,456,520
232,049,592,627,851,629,097
20,725,274,851,017,785,518,433,805,270
```

Your output should be strictly in the following format:
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
