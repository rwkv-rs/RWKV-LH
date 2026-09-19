Every file $\tt file$ resides within a directory containing many other files $\tt dir1, dir2, \cdots, dirj$. The absolute file path of this file is $\tt /dir1/dir2/\cdots/dirj/file$. The root directory is represented by $\tt /$, and files placed directly in the root directory have an absolute file path of the form $\tt /file$.

A symbolic link points to a named directory and can be considered as a shortcut. It can be placed in any directory, but it cannot point to a file. For example, if we place a symbolic link named $\tt hello$ in the root directory pointing to the root directory itself, then $\tt /dir/file$, $\tt /hello/dir/file$, and $\tt /hello/hello/dir/file$ all point to the same file $\tt file$. Another example, if we place a symbolic link named $\tt hi$ in the directory $\tt /dir$ pointing to the root directory, then $\tt /dir/file$, $\tt /dir/hi/dir/file$, and $\tt /dir/hi/dir/hi/dir/file$ all point to the same file $\tt file$. Symbolic links can point to upper, lower, or even the same level directories, but operations like $\tt ./$, $\tt ../$, or $\tt //$ are not allowed.

The question is, can we introduce a symbolic link of length $s$ such that the absolute file path length of a file is exactly $k$?

## Input Format

The first line contains three integers $n, m, k$, representing the number of directories (excluding the root directory), the number of files, and the required path length, respectively.  
The second line contains an integer $s$, representing the length of the symbolic link.  
The next $n$ lines each contain two integers $p_i, l_i$, describing a directory with the directory number $l_i$ and parent directory number $p_i$.  
The next $m$ lines each contain two integers $p_j, l_j$, describing a file with the file length $l_j$ and parent directory number $p_j$.

## Output Format

Output $m$ lines, each containing a string indicating whether it is possible to introduce a symbolic link of length $s$ such that the absolute file path length of the $j$-th file is exactly $k$. If possible, output $\tt YES$; otherwise, output $\tt NO$.

## Sample Input and Output

### Sample Input #1

```
2 4 22
2
0 1
1 5
2 13
2 10
1 4
0 7
```

### Sample Output #1

```
YES
YES
YES
NO
```

## Notes/Hints

### Sample 1 Explanation

Assume the symbolic link is named $\tt LL$, directory names are $\tt a$ and $\tt bbbbb$, and file names are $\tt ccccccccccccc$, $\tt dddddddddd$, $\tt eee$, and $\tt fffffff$. The root directory contains directory $\tt a$ and file $\tt fffffff$, directory $\tt a$ contains directory $\tt bbbbb$ and file $\tt eee$, and directory $\tt bbbbb$ contains files $\tt ccccccccccccc$ and $\tt dddddddddd$. Here is a visual representation:

```plain
/
|-- a
| |-- bbbbb
| | |-- ccccccccccccc
| | +-- dddddddddd
| +-- eeee
+-- fffffff
```

- For the first file, the path that meets the condition is $\tt /a/bbbbb/ccccccccccccc$.
- For the second file, the path that meets the condition is $\tt /a/LL/bbbbb/dddddddddd$.
- For the third file, the path that meets the condition is $\tt /a/LL/a/LL/a/LL/a/eeee$.
- For the fourth file, there is no path that meets the condition.

### Data Size and Constraints

**This problem uses subtask testing.**

- Subtask 1 (33 points): $n, m \le 500$.
- Subtask 2 (33 points): $n, m \le 3 \times 10^3$, the symbolic link is used at most once.
- Subtask 3 (34 points): No special restrictions.

For $100\%$ of the data, $1 \le k, s \le 10^6$, $1 \le m, n \le 3 \times 10^3$.

### Notes

Translated from [BalticOI 2015 Day2 A File Paths](https://boi.cses.fi/files/boi2015_day2.pdf).

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
