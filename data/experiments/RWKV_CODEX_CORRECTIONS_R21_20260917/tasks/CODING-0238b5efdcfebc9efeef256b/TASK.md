There are 32 variables in a program indexed from $0$ to $31$. The $i$-th variable is denoted as $mem[i]$.

Initially, all variables have random values.

The program supports the following operations:

1. `AND a b`: Set `mem[a] = mem[a] AND mem[b]`.
2. `OR a b`: Set `mem[a] = mem[a] OR mem[b]`.
3. `XOR a b`: Set `mem[a] = mem[a] XOR (^) mem[b]`.
4. `NOT a`: Set `mem[a] = NOT (!)mem[a]`.
5. `MOV a b`: Assign the value of `mem[b]` to `mem[a]`.
6. `SET a c`: Set `mem[a]` to `c`.
7. `RANDOM a`: Randomly set `mem[a]` to either $0$ or $1$.
8. `JMP x`: Jump to the $x$-th command.
9. `JZ x a`: If the value of `mem[a]` is $0$, jump to the $x$-th command.
10. `STOP`: Terminate the program.

Executing each command (including the STOP command) takes 1 unit of time. Given multiple programs, determine if each program can terminate without entering an infinite loop.

For each dataset, the first line provides the total number of instructions, $n$ $(1 \leq n \leq 16)$, followed by $n$ lines of instructions.

For each test case, output a line: if the program can terminate, output the shortest time required for it to terminate; if it can't, output `HANGS`.
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
