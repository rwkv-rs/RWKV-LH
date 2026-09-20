> How many rivers wind around, how many mountains stand, where is the city of Jinling?  
> Seeking out famous capitals, exploring strategic locations, dragons and tigers rely on the east of the river.  
> Words left in ink, melodies fall with the tide.  
> Grass and trees have gone through many cycles of withering and flourishing.

——Yin Lin, "Jinling Ballad"

## Problem Description

Nanjing, Jiangsu, also known as Jinling, is a city rich in history and culture. With such a city as its backdrop, the Jiangsu province's college entrance exam mock questions seem particularly challenging and difficult to solve. Qie encountered one such problem during her review, and with the help of Qijin, she quickly solved it. However, Qie felt it was not enough and wanted to use this problem to challenge you. Solving this problem will allow you to enjoy the sweetness shared by Qie and Qijin.

Given four positive integers \(a, b, c, d\), find how many pairs of positive integers \((x, y)\) satisfy the equation:

\[
\frac{a}{x} + \frac{b}{c} = \frac{d}{y}
\]

## Input Format

**This problem contains multiple test cases within a single test point.**

The first line contains an integer \(T\), representing the number of test cases.

The next \(T\) lines each contain four integers \(a, b, c, d\), representing a set of data.

## Output Format

For each test case, output one line containing a single integer representing the answer.

## Sample Input and Output

### Input Sample #1

```
1
1 1 3 2
```

### Output Sample #1

```
3
```

## Notes

### Sample 1 Explanation

We need to find the number of positive integer solutions for the equation \(\frac{1}{x} + \frac{1}{3} = \frac{2}{y}\). The solutions are \((x = 3, y = 3)\), \((x = 6, y = 4)\), and \((x = 15, y = 5)\).

### Data Range and Constraints

There are 20 test points, each worth 5 points.

- For test point 1, \(T = 0\) is guaranteed.
- For test points 2 to 16, there are 15 test points. For \(a, b, c, d\), at least one of the numbers is 1, covering 15 different scenarios, each corresponding to one test point.
- For test points 17 to 20, there are no special constraints.

For all test points, it is guaranteed that \(0 \leq T \leq 20\), \(1 \leq a, b, c, d \leq 10^6\), and \(d \times c \leq 10^6\).

### Hints

- As is well known, number theory is not part of the college entrance exam.
- There are two sample files for this problem, available in the attached song.zip.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
