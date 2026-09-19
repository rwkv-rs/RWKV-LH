"Classification" is a crucial task in artificial intelligence, such as distinguishing whether an image frame in a video contains an abnormal event, identifying if there is a target to be retrieved in a picture, or determining the boundary positions of words in an audio clip.

## Problem Description

Although falling under the category of "artificial intelligence," classification problems can be simply understood as a computer function $f$. It takes a series of data (such as a two-dimensional array representing picture colors, or a string representing text) as input, and $f(x)$ returns either $0$ or $1$, where $1$ indicates that $x$ possesses a certain characteristic and belongs to that classification.

Today, you are tasked with a text classification challenge: identifying whether a sequence of words is written in English or in Chinese pinyin. Below are two texts, one written in Chinese pinyin and the other in English. Can you correctly classify them?

1. While a number of definitions of artificial intelligence (AI) have surfaced over the last few decades, John McCarthy offers the following definition in this 2004 paper, "It is the science and engineering of making intelligent machines, especially intelligent computer programs. It is related to the similar task of using computers to understand human intelligence, but AI does not have to confine itself to methods that are biologically observable."

2. Ren gong zhi neng shi yan jiu、kai fa yong yu mo ni、yan shen he kuo zhan ren.de zhi neng de li lun、fang fa ji ying yong xi tong de yi men xin de ji shu ke xue.

## Input Format

The first line of the input data is the number of text classification tasks $T$.

The next $T$ lines describe each text classification task. The first integer $n$ indicates the number of words, followed by $n$ space-separated strings consisting only of lowercase letters $\tt{a}$ to $\tt{z}$, representing a segment of text to be classified. The input guarantees that there is a space between each word (or each character in Chinese).

## Output Format

For each classification task, output one line. If the text to be classified is written in pinyin, output `Pinyin`; if it is written in English, output `English` (note the capitalization of `Pinyin` and `English`).

## Sample Input and Output

### Sample Input #1

```
2
14 zhe ge ti mu qi shi bi ni xiang xiang de yao jian dan
6 this problem has a simple solution
```

### Sample Output #1

```
Pinyin
English
```

## Notes

For $100\%$ of the data, it is guaranteed that $1 \leq T \leq 10, 10^3 \leq n \leq 10^4$, and the texts are from real, human-readable sources.

> The original full score for this problem was $15\text{pts}$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
