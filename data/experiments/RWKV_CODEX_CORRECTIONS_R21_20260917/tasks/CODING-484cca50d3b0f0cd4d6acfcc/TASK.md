Problem Source: [Zhang\_RQ](https://www.luogu.org/space/show?uid=31565)

## Problem Description

**ZRQ** found that there are $N$ minerals arranged in a row.

He uses a lowercase letter to represent each mineral, and he also found that each mineral has an importance value $V_i$.

**ZRQ** wants to collect a continuous segment of minerals back to the research institute.

He is very strict, and the collected segment of minerals must satisfy **the lexicographical order rank of the lowercase letters equals the sum of the importance values of this segment of minerals.**

**Here, multiple identical substrings appearing at different positions have the same lexicographical order rank.**

For example, if the letter string is `aa`, then the rank of the first `a` and the second `a` is the same, both being `2` (the first is `aa`).

**ZRQ** asks you which different substrings in the original string can be collected?

**Substrings are considered different if they appear at different positions, meaning that identical substrings appearing at different positions should be counted (of course, the sum of importance values equals the rank is a prerequisite).**

For example, there are $4$ minerals, the lowercase letter string is `abcd`, and the importance values are `10 0 1 1`.

We rank all the substrings in descending lexicographical order: `1:d 2:cd 3:c 4:bcd 5:bc 6:b 7:abcd 8:abc 9:ab 10:a`.

Then the rank of the string `d` is $1$ (the largest), and the sum of importance values is $1$, which can be collected.

The rank of the string `cd` is $2$, and the sum of importance values is $2$, which can be collected.

The rank of the string `a` is $10$, and the sum of importance values is $10$, which can be collected.

Other strings do not satisfy this condition, so there are three strings that can be collected.

## Input Format

The first line is a string of length $N$ consisting of lowercase letters, where each character represents a mineral.

The second line contains $N$ integers, representing $V_i$.

## Output Format

One line containing an integer, representing the number of substrings $S$ that can be collected.

Next, $S$ lines each containing two integers $L, R$, representing the left and right endpoints of each collectible substring, sorted by the left endpoint in ascending order as the primary key and the right endpoint in ascending order as the secondary key.

## Sample Input and Output

### Input Sample #1

```
abcd
10 0 1 1
```

### Output Sample #1

```
3
1 1
3 4
4 4
```

### Input Sample #2

```
aaaa
1 1 1 1
```

### Output Sample #2

```
0
```

### Input Sample #3

```
aaa
1 1 1
```

### Output Sample #3

```
2
1 2
2 3
```

### Input Sample #4

```
aaa
1 1 2
```

### Output Sample #4

```
1
1 2
```

## Notes

There are $10$ test points, each worth $10$ points, totaling $100$ points.

For all test points, $N \leq 10^5$, $0 \le V_i \le 1000$. It is guaranteed that each point has no more than $10^5$ collectible substrings.

**Sample #1 explanation** is included in the problem statement.

**Sample #2 explanation:**

None of the substrings meet the condition.

The rank of the string `a` is $4$, and the sum of importance values is $1$.

The rank of the string `aa` is $3$, and the sum of importance values is $2$.

The rank of the string `aaa` is $2$, and the sum of importance values is $3$.

The rank of the string `aaaa` is $1$, and the sum of importance values is $4$.

**Sample #3 explanation:**

The rank of the string `a` is $3$, and the sum of importance values is $1$.

The rank of the string `aa` is $2$, and the sum of importance values is $2$, with two occurrences of the string `aa` at positions $1$~$2$ and $2$~$3$.

The rank of the string `aaa` is $1$, and the sum of importance values is $3$.

**Sample #4 explanation:**

It can be found that the string $2$~$3$ (the second `aa`) does not meet the condition. Its rank remains $2$, but the sum of importance values is $3$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
