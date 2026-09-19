Dyzio is Jasiek's friend and he also likes riddles. Here is a riddle he came up with:

  _Jasiek, here is a piece of string, which has to be cut into smaller pieces. I will not tell you directly how to do it, but look at this sequence of zeros (0) and ones (1). A one at the begining means that the string has to be cut in half. If the first digit was zero, it would be the only digit in the sequence and mean you don't have to cut anything - I want the whole string. If you have to cut the string anyway then after the first 1 I wrote what to do with the left piece (according to the same rules as with the whole string) and then I wrote what to do with the right piece of string (all the time with the same rules of notation). Every time you have to cut the left piece first, only then can you cut the right one. Now start cutting and tell me, how many cuts you have to do until you have cut off the shortest piece._  

 Unfortunately mom hid the scissors from Jasiek, but luckily a computer was at hand and Jasiek quickly wrote a program simulating the string cutting. Can you write such a program?

   
Task 
-----

 Write a program which

- reads (from standard input) description of the way the string is cut,
- counts how many cuts have to be made in order to get the first shortest piece.
- writes out the outcome (to standard output)

## Input Format

Ten test cases (given one under another, you have to process all!). Each test case consists of two lines. In the first line there is a number _n (1<=n<=20000)_. In the second line one zero-one word (a sequence of zeros and ones without spaces between them) of length _n_ - the description of the cutting procedure given by Dyzio.

## Output Format

For every testcase your program should write (to the standard output) only one line with one integer equal to the number of cuts which have to be made in order to get the shortest piece.

## Sample Input and Output

### Sample Input #1

```
9
110011000
[and 9 test cases more]
```

### Sample Output #1

```
4
[and 9 test cases more]
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
