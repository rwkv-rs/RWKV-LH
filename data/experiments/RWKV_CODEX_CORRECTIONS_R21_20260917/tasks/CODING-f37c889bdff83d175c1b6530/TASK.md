It's a beautiful afternoon, and Xiao W and Xiao C are practicing their skills in bundling bamboo poles in a bamboo forest.

The bamboo forest contains an infinite number of identical short bamboo poles, each consisting of $n$ sections.

These bamboo poles are special; each section is dyed with one of 26 possible colors, represented by lowercase English letters from $\underline{a}$ to $\underline{z}$. This means that if you write down the colors from the bottom to the top of a bamboo pole in order, you get a string of lowercase English letters.

Both Xiao W and Xiao C are experts in bundling bamboo poles. They know how to bundle scattered short bamboo poles into one long bamboo pole. Initially, you hold one short bamboo pole as the current bamboo pole. Each time, you can choose a short bamboo pole, and bundle the bottom several sections (could be $0$ sections) of it with the top several sections of the current bamboo pole, one section at a time, while the remaining sections of the short bamboo pole extend outward. This way, you get a longer bamboo pole. Note that the bottom of the bamboo pole is the end closer to the root and should not be reversed.

Xiao W has high aesthetic standards for bamboo poles. He has a peculiar habit when bundling bamboo poles: if two sections of two bamboo poles are bundled together, they must be of the same color.

Let's assume a short bamboo pole has colors from bottom to top as $\underline{aba}$.

Then two bamboo poles can be bundled end-to-end to get a bamboo pole with colors $\underline{abaaba}$; or the top section $\underline{a}$ of the first pole can be bundled with the bottom section $\underline{a}$ of the second pole to get a bamboo pole with colors $\underline{ababa}$; or each section can be bundled correspondingly to get a bamboo pole with colors $\underline{aba}$.

If we bundle another bamboo pole on top of a bamboo pole with colors $\underline{ababa}$, we can get $\underline{ababaaba}$, $\underline{abababa}$, and $\underline{ababa}$ in three different cases.

However, Xiao C has a different opinion on this matter. He believes that Xiao W cannot bundle many bamboo poles of different lengths. Xiao W is very unconvinced, so he turns to you—now please calculate how many different lengths of bamboo poles Xiao W can bundle, given that the length of the bamboo pole does not exceed $w$. Here, the length of the bamboo pole refers to the number of sections from the bottom to the top.

Note: If $w < n$, there are no valid lengths, and the answer is $0$.

## Input Format

The input file jie.in consists of $T$ lines, where $T$ is the number of test cases.

For each test case, the first line contains two positive integers $n$ and $w$, representing the length of the short bamboo pole and the length limit of the bamboo pole, respectively.

The second line of each test case contains a string of length $n$, consisting only of lowercase English letters, representing the colors of the short bamboo pole from bottom to top.

## Output Format

The output file is jie.out.

The output consists of $T$ lines, each containing an integer representing the number of different lengths of bamboo poles that can be bundled.

## Sample Input and Output

### Sample Input #1

```
1
4 11
bbab
```

### Sample Output #1

```
5
```

### Sample Input #2

```
2
44 1000
baaaaaabaabbaaabbbbabbbaaabbbababaaabaaabaaa
41 1000
abaabbabaaabaabbbbbbbbbbbababbbbaaabaabbb
```

### Sample Output #2

```
195
24
```

## Notes/Hints

**Sample Explanation #1**

There are 6 different cases of bamboo poles that can be bundled with lengths not exceeding 11:

$bbab$
$bbabbab$
$bbabbbab$
$bbabbabbab$
$bbabbabbbab$
$bbabbbabbab$

The last two bamboo poles have the same length, so there are 5 different lengths in total. The lengths are: $4$, $7$, $8$, $10$, $11$.

**Data Size and Constraints**

For all test data, it is guaranteed that all strings consist of lowercase letters.

Each test point adheres to the following constraints:

![QQ20180128185500.png](https://www.z4a.net/images/2018/01/28/QQ20180128185500.png)

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
