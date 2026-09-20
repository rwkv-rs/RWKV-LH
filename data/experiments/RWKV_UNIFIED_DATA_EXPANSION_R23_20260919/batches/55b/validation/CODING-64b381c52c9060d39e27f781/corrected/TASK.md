Given a virtual keyboard displayed on a TV screen with $r$ rows and $c$ columns, you can move the cursor on the screen to print text using five control keys: up, down, left, right, and select. Initially, the cursor is at the top-left corner of the keyboard. Each directional key press moves the cursor to the next position in that direction that contains a different character from the current one, if such a position exists; otherwise, the cursor does not move. Each select key press prints the character at the cursor's current position.

Determine the minimum number of key presses required to print a given text, including a newline character at the end.

## Input Format

The first line of the input contains two integers $r$ and $c$ ($1 \leq r, c \leq 50$), representing the number of rows and columns of the virtual keyboard grid. The next $r$ lines each contain $c$ characters, specifying the layout of the virtual keyboard. The characters can be uppercase letters, digits, a dash, and an asterisk (representing Enter). Each character corresponds to a unique key, which consists of one or more connected grid squares forming a contiguous region. The last line of the input contains the text to be typed, which is a non-empty string of up to $10,000$ characters excluding the asterisk.

## Output Format

Output the minimal number of key presses necessary to type the entire text, including the Enter key at the end. It is guaranteed that the text can be typed.

## Sample Input and Output

### Sample Input #1

```
4 7
ABCDEFG
HIJKLMN
OPQRSTU
VWXYZ**
CONTEST
```

### Sample Output #1

```
30
```

### Sample Input #2

```
5 20
12233445566778899000
QQWWEERRTTYYUUIIOOPP
-AASSDDFFGGHHJJKKLL*
--ZZXXCCVVBBNNMM--**
--------------------
ACM-ICPC-WORLD-FINALS-2015
```

### Sample Output #2

```
160
```

### Sample Input #3

```
2 19
ABCDEFGHIJKLMNOPQZY
X*****************Y
AZAZ
```

### Sample Output #3

```
19
```

### Sample Input #4

```
6 4
AXYB
BBBB
KLMB
OPQB
DEFB
GHI*
AB
```

### Sample Output #4

```
7
```

## Notes/Hints

Time limit: 3000 ms, Memory limit: 1048576 kB.

International Collegiate Programming Contest (ACM-ICPC) World Finals 2015

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
