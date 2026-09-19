A set of TED lights needs to be tested. You are given the on/off states of several independent TED lights and need to determine if each group of states represents a descending sequence of numbers (the numbers must be consecutive).

The seven segments of a TED light could be damaged; damaged segments cannot light up again, but undamaged segments may become damaged later on.

## Input and Output Examples

### Input Example #1

```
1
YYYYNYY
2
NNNNNNN
NNNNNNN
2
YYYYYYY
YYYYYYY
3
YNYYYYY
YNYYNYY
NYYNNYY
3
YNYYYYN
YNYYNYN
NYYNNYN
3
YNYYYYN
YNYYNYN
NYYNYYN
4
YYYYYYY
NYYNNNN
NNYYYYN
NNNYNNN
3
NNNNNNN
YNNNNNN
NNNNYNN
0
```

### Output Example #1

```
MATCH
MATCH
MISMATCH
MATCH
MATCH
MISMATCH
MATCH
MATCH
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
