Professor B. Heif is conducting experiments with South American bees he discovered during his expedition in the Brazilian tropical rainforest. These bees can produce high-quality honey, unlike their European and North American counterparts. Unfortunately, these bees do not reproduce well. Professor Heif believes this is related to the positioning of different larvae (worker bees, queen bees) in the hive, which is influenced by environmental conditions, and thus differs between his laboratory and the tropical rainforest.

To prove his theory, Professor Heif wants to determine the number of different larvae placement arrangements. To proceed, he needs to measure the distance between two hives containing larvae. The professor labels the hives as follows: he marks any hive as 1, and then labels the subsequent hives in a clockwise direction as 2, 3, and so on, as shown in the diagram:

![](https://cdn.luogu.org/upload/vjudge_pic/UVA808/9bab4a64afdd472dc2664e3eff03743e904c3d4a.png)

For example, hive 19 and hive 30 are 5 hives apart. The shortest path connecting these two hives passes through: 19-7-6-5-15-30, so you must move to adjacent hives 5 times to get from 19 to 30.

Professor Heif needs your help to write a program that calculates the distance between each pair of hives.

## Input
The input consists of multiple lines, each containing two integers \(a\) and \(b\) (\(a, b \leq 10000\)), representing the labels of the hives. These integers are always positive, except for the last line where \(a = b = 0\), which indicates the end of the input file and should not be processed.

## Output
For each pair of integers \((a, b)\) in the input file, output the distance between the hives labeled as \(a\) and \(b\). This distance is the minimum number of movements required to travel from \(a\) to \(b\).

### Sample Input
```
19 30
0 0
```
### Sample Output
```
The distance between cells 19 and 30 is 5.
```

## Input/Output Samples

### Input Sample #1

```
19 30
0 0
```

### Output Sample #1

```
The distance between cells 19 and 30 is 5.
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
