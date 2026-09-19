### Problem Description

Piotr is organizing a competition that requires $n$ problems, with each problem's name starting sequentially with the letters $A$, $B$, $C$, and so on. Piotr has $n$ groups of problems, and he needs to select one problem from each group to form the competition. How should he select the problems so that their names start with $A$, $B$, $C$, etc., and one problem is selected from each group?

There is a guarantee of a unique solution.

### Input Format

The first line contains an integer $T$, representing the number of test cases. For each test case:

The first line contains an integer $n$, indicating the number of contest problems and the number of problem groups that Piotr has.

The next $n$ lines each begin with an integer $k_i$, indicating the number of problems in the $i$-th problem group, followed by $k_i$ strings representing the names of the problems in that group.

**Note: After inputting the strings, the first letter of each string should be capitalized into an uppercase English letter, and the remaining letters should be converted to lowercase before proceeding. The output should also be in this format.**

### Output Format

For each test case:

The first line should output `Case #x:`, where $x$ is the case number.

The following $n$ lines should each contain a string representing the name of the $i$-th problem in the competition.

## Input and Output Example

### Input Example #1

```
4
3
2 Apples Oranges
1 Bananas
5 Apricots Blueberries Cranberries Zuccini Yams
1
1 ApPlEs
2
2 a b
1 axe
4
4 Aa Ba Ca Da
3 Ab Bb Cb
2 Ac Bc
1 Ad
```

### Output Example #1

```
Case #1:
Apples
Bananas
Cranberries
Case #2:
Apples
Case #3:
Axe
B
Case #4:
Ad
Bc
Cb
Da
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
