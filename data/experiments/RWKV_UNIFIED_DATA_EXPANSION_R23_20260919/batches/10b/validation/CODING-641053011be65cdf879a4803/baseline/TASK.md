Victor tries to write his own text editor, with word correction included. However, the rules of word correction are really strange. Victor thinks that if a word contains two consecutive vowels, then it's kinda weird and it needs to be replaced. So the word corrector works in such a way: as long as there are two consecutive vowels in the word, it deletes the first vowel in a word such that there is another vowel right before it . If there are no two consecutive vowels in the word, it is considered to be correct. You are given a word s . Can you predict what will it become after correction? In this problem letters a , e , i , o , u and y are considered to be vowels .

## Time Limit and Memory Limit

Time Limit: 1 second
Memory Limit: 256 megabytes

## Input Specification

The first line contains one integer n ( 1 ≤  n  ≤ 100 ) — the number of letters in word s before the correction. The second line contains a string s consisting of exactly n lowercase Latin letters — the word before the correction.

## Output Specification

Output the word s after the correction.

## Examples

### Input #1
5
weird

### Output #1
werd

### Input #2
4
word

### Output #2
word

### Input #3
5
aaeaa

### Output #3
a

## Note

Explanations of the examples: There is only one replace: w ei rd  werd; No replace needed since there are no two consecutive vowels; aa eaa ae aa aa a aa a.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
