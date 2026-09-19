Tomato Automata is a cool little program. It takes an infinite sequence of 1s and 0s as input and outputs a numerical sequence. It is widely used in the Stanescu Operating System (SOS).

Tomato Automata is written in a very simple language called Tomato. Here are its specifications:

1. The Tomato language is a very simple yet powerful language.

2. Each line contains exactly one command, and the program executes starting from the first line.

3. Line numbers in a Tomato program are sequential integers from $1$ to $N$ ($N \le 100000$). $N$ will be provided in the input.

4. The Tomato language has only five commands: `ifgo`, `jump`, `pass`, `loop`, and `die`.

5. During code execution, each command will print its line number.

6. The `ifgo` command takes a single argument. When executing `ifgo x`, the program reads a bit (0 or 1) from the input stream. If the bit is 1, it jumps to line `x`; otherwise, it continues to the next line.

7. The `jump` command also takes a single argument. When executing `jump x`, the program will jump directly to line `x`.

8. The `pass` command takes no arguments. It does nothing other than printing the line number.

9. The `die` command takes no arguments. It prints the line number and immediately terminates the program. It will not appear inside a loop.

10. The `loop` command takes two arguments. `loop s x` means that the program will execute the lines from line `s` to the current line `x` times (including the first time it reaches line `s`). It is guaranteed that line `s` is before the line containing the `loop`.

11. `jump` and `ifgo` commands can only jump within the innermost loop. They cannot jump from outside a loop into a loop or from inside a loop to the outside.

12. Loops can only be strictly nested; there will be no overlapping loop intervals that are not fully contained within each other.

13. Unless the last line of the program is a `die` command, after the last line is executed, the program will start executing from the first line again.

14. There may be multiple whitespace characters before and after a command and its parameters.

15. Each line of the program has a maximum of 80 characters (including whitespace).

Given several Tomato programs, determine the maximum length of the string each program can print. If a program may cause an infinite loop, output $infinity$.

# Input Format

Input consists of several programs, each separated by a blank line. Each program is guaranteed to be correct.

# Output Format

For each program, output the maximum length of the string it can print. If the program may cause an infinite loop, output $infinity$. It is guaranteed that the answer will not exceed $10^9$.
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
