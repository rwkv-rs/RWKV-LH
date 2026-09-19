## Translation
### Problem Summary
A puzzle game where each puzzle piece has a unique shape. Consider the following puzzle example:
~~~~
11223
11223
12233
11233
11133
~~~~
It consists of the following pieces:
~~~~
11
11
1
11
111

  22
  22
22
  2

  3
  3
33
33
33
~~~~
You need to write a program that can use these pieces to assemble them into a complete **square**.

---------------------------

### Input Format:
The input consists of multiple datasets.

The first line contains the length $l$ of the **complete** puzzle. ($l \le 20$)

The second line contains the number of puzzle pieces $m$. ($m \le 9$)

The following lines describe each puzzle piece, made up of numbers.

Each dataset ends with a "#", with a "0" marking the end of input.
### Output Format:
Output the complete assembled puzzle.

## Example Input/Output

### Example Input #1

```
7
6
3333
33
3333
33
33
7 7
7 7
7777
88888
6
666
66
22
222
2
5
55
55
555
5 5
#
0
```

### Example Output #1

```
8777333
8733333
8733323
8777323
8655222
6665552
6655555
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
