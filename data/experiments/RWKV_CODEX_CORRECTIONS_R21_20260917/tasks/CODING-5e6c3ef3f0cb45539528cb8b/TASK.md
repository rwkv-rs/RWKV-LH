Amoeba is Xiaoqiang's good friend.

In Xiaoqiang's eyes, Amoeba is a literary youth with high essay scores. To understand the essence of exam essays, Xiaoqiang sought advice from Amoeba. Amoeba showed Xiaoqiang several essays, which Xiaoqiang found oddly familiar, as if they were pieced together from some model essays. Xiaoqiang couldn't help but give Amoeba a suspicious look, only to find Amoeba wearing a sly smile.

To convincingly demonstrate how "familiar" Amoeba's essays are, Xiaoqiang devised a quantitative metric for the "familiarity level" of essays: $L_0$. Xiaoqiang first converted the essays into $01$ strings. Then, he collected articles from various famous writers, converted them into $01$ strings as well, and compiled a "standard essay library" containing $M$ $01$ strings.

Xiaoqiang believes that if a $01$ string is at least $L$ characters long and appears as a continuous substring in one of the strings in the standard essay library, then it is "familiar". For an essay (a $01$ string) $A$, if $A$ can be divided into several substrings such that the total length of the "familiar" substrings is at least $90\%$ of the total length of $A$, then $A$ is considered a "familiar article". $L_0$ is the maximum value of $L$ that allows $A$ to be a "familiar article" (if no such $L$ exists, then $L_0 = 0$).

For example:

Xiaoqiang's essay library contains the following $2$ strings:

```cpp
10110
000001110
```
There is an essay to be evaluated:

```cpp
1011001100
```
Xiaoqiang calculates that the maximum value of $L$ for this essay is $4$, because the essay can be seen as $10110 + 0110 + 0$, where $10110$ and $0110$ are judged to be "familiar". When $L = 5$ or larger, there is no valid way to split the essay as required. Therefore, the $L_0$ of this essay is $4$. Xiaoqiang believes that Amoeba's $L_0$ value is significantly higher than that of other students. Please help him verify this.

## Input Format

The first line of input contains two integers $N, M$, representing the number of essays to be checked and the number of lines in Xiaoqiang's standard essay library, respectively.

The next $M$ lines are $01$ strings representing the standard essay library.

The following $N$ lines are $01$ strings representing the $N$ essays.

## Output Format

The output contains $N$ lines, each line containing an integer representing the $L_0$ value of the corresponding essay.

## Sample Input and Output

### Input Sample #1

```
1 2
10110
000001110
1011001100
```

### Output Sample #1

```
4
```

## Notes

For $30\%$ of the test cases, the input file size does not exceed $1000$ bytes.

For $50\%$ of the test cases, the input file size does not exceed $61000$ bytes.

For $80\%$ of the test cases, the input file size does not exceed $250000$ bytes.

For $100\%$ of the test cases, the input file size does not exceed $1100000$ bytes.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
