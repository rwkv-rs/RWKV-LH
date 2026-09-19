A word is a string consisting of uppercase or lowercase letters, and it can also end with punctuation marks (`.`, `?`, `!`). A name is a word that **has only the first letter as uppercase**.

A sentence is a string composed of words, and it ends with a punctuation mark (`.`, `?`, `!`).

Given $N$ sentences, Mirko wants you to count how many names are in each sentence.

## Input Format

The first line contains a positive integer $N$, representing the number of sentences.

The second line contains these $N$ sentences. The total number of characters in these sentences will not exceed $10^3$.

## Output Format

Output $N$ lines, each containing a positive integer. The $i$-th line represents the total number of names in the $i$-th sentence.

## Sample Input and Output

### Sample Input #1

```
1
Spavas li Mirno del Potro Juan martine?
```

### Sample Output #1

```
4
```

### Sample Input #2

```
2
An4 voli Milovana. Ana nabra par Banana. 
```

### Sample Output #2

```
1
2
```

## Notes/Hints

### Sample Explanation

#### Sample 2 Explanation

In the first sentence, the name is `Milovana`, totaling $1$; in the second sentence, the names are `Ana` and `Banana`, totaling $2$. Note that in the first sentence, although `An4` starts with an uppercase letter, it contains a digit, so it is not a name.

### Data Size and Constraints

For $40\%$ of the test cases, $N=1$.

For $100\%$ of the test cases, $1 \le N \le 5$.

### Notes
**This problem is translated from [COCI2016-2017](https://hsin.hr/coci/archive/2016_2017/) [CONTEST #3](https://hsin.hr/coci/archive/2016_2017/contest3_tasks.pdf) _T1 Imena_**.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
