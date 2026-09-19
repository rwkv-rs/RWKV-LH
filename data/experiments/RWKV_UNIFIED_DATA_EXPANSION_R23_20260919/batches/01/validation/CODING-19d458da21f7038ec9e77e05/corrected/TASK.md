We define a test sentence as a string containing all lowercase English letters.

Given $N$ words, how many test sentences can be formed at most using these words?

Each word can only be used once in a test sentence, and the order of words in the sentence does not matter, meaning `uvijek jedem sarmu` and `jedem sarmu uvijek` are considered equal.

## Input Format

The first line of input contains an integer $N$, the number of words.

The next $N$ lines each contain a word, with a length not exceeding $100$.

All words are guaranteed to be unique.

## Output Format

Output the maximum number of test sentences that can be formed.

## Sample Input and Output

### Sample Input #1

```
9
the
quick
brown
fox
jumps
over
a
sleazy
dog
```

### Sample Output #1

```
2
```

### Sample Input #2

```
3
a
b
c
```

### Sample Output #2

```
0
```

### Sample Input #3

```
15
abcdefghijkl
bcdefghijklm
cdefghijklmn
defghijklmno
efghijklmnop
fghijklmnopq
ghijklmnopqr
hijklmnopqrs
ijklmnopqrst
jklmnopqrstu
klmnopqrstuv
lmnopqrstuvw
mnopqrstuvwx
nopqrstuvwxy
opqrstuvwxyz
```

### Sample Output #3

```
8189
```

## Notes

### Data Range and Constraints

$1 \le N \le 25$.

### Sample Explanation

#### Sample 1 Explanation

All words except `a` must be used in the test sentence because each word contains a letter not found in other words. Therefore, there are two solutions. The first is a sentence containing all words, and the second is a sentence composed of all words except `a`.

#### Sample 3 Explanation

This sample consists of consecutive lowercase English letters.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
