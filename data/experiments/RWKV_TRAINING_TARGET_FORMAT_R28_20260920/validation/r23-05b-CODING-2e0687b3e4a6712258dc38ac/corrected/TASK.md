Before becoming a successful trader William got a university degree. During his education an interesting situation happened, after which William started to listen to homework assignments much more attentively. What follows is a formal description of the homework assignment as William heard it:

You are given a string $$$s$$$ of length $$$n$$$ only consisting of characters "a", "b" and "c". There are $$$q$$$ queries of format ($$$pos, c$$$), meaning replacing the element of string $$$s$$$ at position $$$pos$$$ with character $$$c$$$. After each query you must output the minimal number of characters in the string, which have to be replaced, so that the string doesn't contain string "abc" as a subsequence. A valid replacement of a character is replacing it with "a", "b" or "c".

A string $$$x$$$ is said to be a subsequence of string $$$y$$$ if $$$x$$$ can be obtained from $$$y$$$ by deleting some characters without changing the ordering of the remaining characters.

Input

The first line contains two integers $$$n$$$ and $$$q$$$ $$$(1 \le n, q \le 10^5)$$$, the length of the string and the number of queries, respectively.

The second line contains the string $$$s$$$, consisting of characters "a", "b" and "c".

Each of the next $$$q$$$ lines contains an integer $$$i$$$ and character $$$c$$$ $$$(1 \le i \le n)$$$, index and the value of the new item in the string, respectively. It is guaranteed that character's $$$c$$$ value is "a", "b" or "c".

Output

For each query output the minimal number of characters that would have to be replaced so that the string doesn't contain "abc" as a subsequence.

Examples

Input

9 12
aaabccccc
4 a
4 b
2 b
5 a
1 b
6 b
5 c
2 a
1 a
5 a
6 b
7 b

Output

0
1
2
2
1
2
1
2
2
2
2
2

Note

Let's consider the state of the string after each query:

1. $$$s = $$$"aaaaccccc". In this case the string does not contain "abc" as a subsequence and no replacements are needed.
2. $$$s = $$$"aaabccccc". In this case 1 replacements can be performed to get, for instance, string $$$s = $$$"aaaaccccc". This string does not contain "abc" as a subsequence.
3. $$$s = $$$"ababccccc". In this case 2 replacements can be performed to get, for instance, string $$$s = $$$aaaaccccc". This string does not contain "abc" as a subsequence.
4. $$$s = $$$"ababacccc". In this case 2 replacements can be performed to get, for instance, string $$$s = $$$"aaaaacccc". This string does not contain "abc" as a subsequence.
5. $$$s = $$$"bbabacccc". In this case 1 replacements can be performed to get, for instance, string $$$s = $$$"bbacacccc". This string does not contain "abc" as a subsequence.
6. $$$s = $$$"bbababccc". In this case 2 replacements can be performed to get, for instance, string $$$s = $$$"bbacacccc". This string does not contain "abc" as a subsequence.
7. $$$s = $$$"bbabcbccc". In this case 1 replacements can be performed to get, for instance, string $$$s = $$$"bbcbcbccc". This string does not contain "abc" as a subsequence.
8. $$$s = $$$"baabcbccc". In this case 2 replacements can be performed to get, for instance, string $$$s = $$$"bbbbcbccc". This string does not contain "abc" as a subsequence.
9. $$$s = $$$"aaabcbccc". In this case 2 replacements can be performed to get, for instance, string $$$s = $$$"aaacccccc". This string does not contain "abc" as a subsequence.
10. $$$s = $$$"aaababccc". In this case 2 replacements can be performed to get, for instance, string $$$s = $$$"aaacacccc". This string does not contain "abc" as a subsequence.
11. $$$s = $$$"aaababccc". In this case 2 replacements can be performed to get, for instance, string $$$s = $$$"aaacacccc". This string does not contain "abc" as a subsequence.
12. $$$s = $$$"aaababbcc". In this case 2 replacements can be performed to get, for instance, string $$$s = $$$"aaababbbb". This string does not contain "abc" as a subsequence.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
