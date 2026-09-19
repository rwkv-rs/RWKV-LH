A cyclic permutation is an encryption technique that involves selecting a cycle \( k \) and a permutation of the first \( k \) numbers. To encrypt a message, it is first broken into groups of \( k \) characters, and the given permutation is applied. Decryption involves taking a group of \( k \) characters and performing the inverse permutation. This encrypts "Mary" as "yMra", and "Maryan" as "yMra?a?n". Once the permutation is known, it can be reverse-applied to other encrypted messages to recover the original text.

Write a program that reads a triplet of (plaintext, cipher1, cipher2) and determines if the cyclic permutation encryption method was used for each pair (plaintext, cipher1). If it was, determine the value of \( k \) and the permutation function, and apply the inverse permutation to cipher2 to recover the corresponding plaintext.

## Input

The input will consist of a series of triplets (plaintext, cipher1, cipher2). Each line will be at most 80 characters long. The first two strings (of length \( n \)) represent the first \( n \) characters of the plaintext; this does not imply that \( n \) is a multiple of \( k \). The input will end with a single "#".

## Output

The output will consist of a series of lines, one corresponding to every three lines in the input. If a permutation cycle is found, apply the inverse permutation to cipher2, with '?' used where necessary.

If no cyclic permutation can be found (with a period less than or equal to the length of the plaintext and cipher1), it will print cipher2.

If more than one cyclic permutation can map the plaintext to cipher1, then apply the cyclic permutation with the smallest \( k \) value. At most one permutation function will match the data.

## Input and Output Examples

### Input Example #1

```
Mary had a little lamb!!
aMyrh daa l tilt ealbm!!
hTsii s aetts
Foobar
blargg
No cycle
abc
bca
abcd
#
```

### Output Example #1

```
This is a test
No cycle
cab?d?
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
