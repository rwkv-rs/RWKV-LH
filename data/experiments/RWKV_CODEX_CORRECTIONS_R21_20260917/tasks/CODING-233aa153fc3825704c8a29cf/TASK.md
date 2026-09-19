Given several strings, calculate the percentage of each string in all the strings.

**【Input Format】**

The first line contains an integer $t$, representing the number of data sets.

In each of the $t$ data sets, there are multiple lines, each containing a string (which may include spaces), representing the input strings.

There is a blank line separating each data set.

**【Output Format】**

For each data set, output multiple lines, each showing a string (in lexicographical order) and its percentage among all words (rounded to 4 decimal places).

There should be a blank line separating the outputs of each data set.

**【Data Constraints】**

For $100\%$ of the data, the number of unique strings does not exceed $10^4$, the total number of strings does not exceed $10^6$, and the length of each string does not exceed $30$.

## Sample Input

### Sample Input #1

```
1

Red Alder
Ash
Aspen
Basswood
Ash
Beech
Yellow Birch
Ash
Cherry
Cottonwood
Ash
Cypress
Red Elm
Gum
Hackberry
White Oak
Hickory
Pecan
Hard Maple
White Oak
Soft Maple
Red Oak
Red Oak
White Oak
Poplan
Sassafras
Sycamore
Black Walnut
Willow

```

### Sample Output #1

```
Ash 13.7931
Aspen 3.4483
Basswood 3.4483
Beech 3.4483
Black Walnut 3.4483
Cherry 3.4483
Cottonwood 3.4483
Cypress 3.4483
Gum 3.4483
Hackberry 3.4483
Hard Maple 3.4483
Hickory 3.4483
Pecan 3.4483
Poplan 3.4483
Red Alder 3.4483
Red Elm 3.4483
Red Oak 6.8966
Sassafras 3.4483
Soft Maple 3.4483
Sycamore 3.4483
White Oak 10.3448
Willow 3.4483
Yellow Birch 3.4483
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
