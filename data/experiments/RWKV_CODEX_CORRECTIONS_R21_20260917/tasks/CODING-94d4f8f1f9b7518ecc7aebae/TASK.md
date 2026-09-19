Cube Word is a special word-filling game. Before starting, you need to choose the side length $a$ of the cube, and then you can create a cube consisting of $a^3$ unit cubes. This large cube has 12 edges. Then, you remove all unit cubes that do not touch the edges of the large cube. The following image shows the final cube when $a=6$.

![](https://cdn.luogu.com.cn/upload/image_hosting/zzs7dshw.png)

Finally, you need to fill each remaining unit cube with a letter. After filling the cube, each edge should form a meaningful word. Each edge can be read in both directions, as long as it makes sense in one direction.

The following image shows a cube when $a=6$. Some unit cubes have already been filled with letters. You can already read the words **SUBMIT**, **ACCEPT**, and **TURING** along three edges of the large cube.

![](https://cdn.luogu.com.cn/upload/image_hosting/jzpyzoeu.png)

Given a series of meaningful words, each word can appear on any legal edge of the cube. Calculate the number of different cubes that can be constructed, modulo $998244353$.

Even if a cube can be transformed into another cube by rotation or mirroring, these two cubes are considered **different**.

## Input Format

The first line contains an integer $n$, the number of words.

The next $n$ lines each contain a word that can appear on the edges of the large cube. The length of each word is between 3 and 10, inclusive.

All words are guaranteed to be unique.

## Output Format

Output a single integer, the number of different cubes that can be constructed, modulo $998244353$.

## Sample Input and Output

### Sample Input #1

```
1
radar
```

### Sample Output #1

```
1
```

### Sample Input #2

```
1
robot
```

### Sample Output #2

```
2
```

### Sample Input #3

```
2
FLOW
WOLF
```

### Sample Output #3

```
2
```

### Sample Input #4

```
2
baobab
bob
```

### Sample Output #4

```
4097
```

### Sample Input #5

```
3
TURING
SUBMIT
ACCEPT
```

### Sample Output #5

```
162
```

### Sample Input #6

```
3
MAN1LA
MAN6OS
AN4NAS
```

### Sample Output #6

```
114
```

## Notes/Hints

### Sample Explanation #1

In the first sample, the only possibility is that all edges of the cube are filled with the word **radar**.

### Sample Explanation #2

In the second sample, there are two cubes, one of which can be obtained by rotating the other. All edges of the cube are filled with the word **robot**, and the difference between the two cubes is whether the letter in the bottom left corner is **r** or **t**.

### Sample Explanation #3

The third sample is similar to the second, noting that the reading direction does not affect the answer.

### Sample Explanation #4

In the fourth sample, if the word **bob** is filled on all edges of the cube, there is one cube. There are $2^{12} = 4096$ cubes where all edges are filled with the word **baobab** (for each of the 12 edges, we have two possible reading orders).

### Data Range

For all data, $1 \le n \le 10^5$.

Detailed subtask constraints and scores are as follows:

| Subtask Number | Constraints | Score |
| :------------: | :---------: | :---: |
| 1 | Words contain only lowercase `a` to `f` | $21$ |
| 2 | Words contain only lowercase `a` to `p` | $29$ |
| 3 | Words contain lowercase `a` to `p` and uppercase `A` to `P` | $34$ |
| 4 | Words contain lowercase `a` to `z`, uppercase `A` to `Z`, and digits `0` to `9` | $16$ |

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
