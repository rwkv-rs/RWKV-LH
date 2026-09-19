The correctness of the name "Suffix Balanced Tree" is questionable, as the definition of "Weight Balanced Tree" given by clj is ambiguous.

Since I am not proficient in string manipulation, I did not verify this.

## Problem Description

You are given a string `init` and are required to support three operations:

1. Insert several characters at the end of the current string.
2. Delete several characters from the end of the current string.
3. Query how many times the string $s$ appears in the current string as a contiguous substring.

You must support these operations online.

## Input Format

The first line contains a number $q$ representing the number of operations.

The second line is a string representing the initial string `init`.

The next $q$ lines, each containing two strings `Type Str`.

If `Type` is `ADD`, it means to insert at the end.

If `Type` is `DEL`, it means to delete from the end.

If `Type` is `QUERY`, it means to query how many times a certain string appears in the current string.

To reflect online operations, you need to maintain a variable `mask`, initially set to $0$.

After reading the string `Str`, use this process to decode it into the actual string `TrueStr` for the query.

When querying, query `TrueStr` and output the answer `Result` in one line.

Then update `mask = mask xor Result`.

When inserting, append `TrueStr` to the end of the current string.

![](https://cdn.luogu.com.cn/upload/image_hosting/whqt9ff9.png)

## Output Format

For each `QUERY` operation, output one line containing an integer representing the answer.

## Sample Input and Output

### Input Sample #1

```
3
A
QUERY B
ADD BBABBBBAAB
DEL 1
```

### Output Sample #1

```
0
```

## Notes

The length of the string changes and the initial length are both $\le 8 \times 10^5$, the number of queries is $\le 10^5$, and the total length of queries is $\le 3 \times 10^6$.

The character set is uppercase letters, and note that strings for both `ADD` and `QUERY` operations need to be decompressed.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
