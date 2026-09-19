#### 1. Problem Description

Your task is to create a maze drawing program. This maze can include uppercase letters A-Z, `*` (asterisk), and spaces.

#### 2. Input Format

Your program will receive maze information from the input. The input consists of multiple lines, each containing a series of numbers and characters, with numbers preceding characters. The format is `<number><char><number><char>`, where `<number>` represents a digit and `<char>` represents a character. It means that the `<char>` should be repeated `<number>` times, e.g., `2T` translates to the string `TT`. Note that there may be two or even more `<number>`s, in which case the numbers should be summed. For example, `11T` is equivalent to `2T`.

There are various possibilities for `<char>`. If it is an uppercase letter or an asterisk, it should be output as is. If it is `b`, output a space. For example, `1A1K1b2*1I1O1I2*` represents `AK **IOI**`.

If a `!` (exclamation mark) is encountered in the input, output a newline. This symbol does not have a number preceding it.

After completing one line of input, you should output a newline. For instance:

```
1A1B
1C1D
```

corresponds to:

```
AB
CD
```

and not `ABCD` (even though there is no exclamation mark in the input).

Different maze descriptions are separated by empty lines. When this occurs, you should output a blank line (that is, two newlines). (The sample output on the site does not include a blank line, but the original problem PDF does.) The input file will end with the end-of-file marker.

#### 3. Output Format

For each description in the input file, draw the corresponding maze. There is no limit to the number of lines in a maze or the number of mazes in the file, but any single line will not exceed 132 characters.

## Sample Input and Output

### Sample Input #1

```
1T1b5T!1T2b1T1b2T!1T1b1T2b2T!1T3b1T1b1T!3T3b1T!1T3b1T1b1T!5T1*1T
11X21b1X
4X1b1X
```

### Sample Output #1

```
T TTTTT
T T TT
T T TT
T TT
TTT T
T TT
TTTTT*T
XX X
XXXX X
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
