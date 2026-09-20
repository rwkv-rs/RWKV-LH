Zvonkec is yet another programmer employed in a small company. Every day he has to refactor one file of source code. Much to his dismay, the source is usually far from being clear and tidy. He is especially bothered by uneven indentation, i.e. the number of tabulators (tabs) indenting each line.

Fortunately, his editor has a command to select a group of consecutive lines and add or delete a character from the start of each one. Help Zvonkec tidy up the code as quickly as possible.

You are given the number of lines N, a sequence specifying the current number of tabs at the start of each line, and a sequence specifying the required number of tabs at the start of each line.

Zvonkec can execute any number of commands consisting of:

● selecting any number of consecutive lines  
● adding or deleting a single tab to/from the front of each of the selected lines

The two actions above comprise a single command, regardless of the number of selected lines. It should be noted that it is forbidden to delete more tabs from a line than are actually present at the start of a line, as the editor would start deleting characters other than tabs.

You are asked to calculate the minimum number of commands required to tidy up the code.

## Input Format

The first line of input contains a positive integer N (N

The second line contains a sequence of N integers Pi (0

The third line contains a sequence of N integers Ki (0

## Output Format

The first and only line of output must contain the required number, as specified in the problem statement.

## Sample Input and Output

### Sample Input #1

```
\n3 \n3 4 5 \n6 7 8\n\n
```

### Sample Output #1

```
\n3\n\nInput:\n4 \n1 2 3 4 \n3 1 1 0\n\nOutput:\n6\n\nInput:\n4\n5 4 5 5\n1 5 0 1\n\nOutput:\n10\n\n
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
