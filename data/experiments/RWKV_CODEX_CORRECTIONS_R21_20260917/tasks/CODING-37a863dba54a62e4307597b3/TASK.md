### Background:
We define a valid bracket sequence as follows:
1. An empty sequence is a valid bracket sequence.
2. If S is a valid bracket sequence, then (S) and \[S\] are also valid bracket sequences.
3. If A and B are valid bracket sequences, then AB is a valid bracket sequence.

For example, the following sequences are all valid bracket sequences:

`(),[],(()),([]),()[],()[()]`

While the following are not valid bracket sequences:

`(,[,),)(,([)],([]`

### Problem Description:
You are given some bracket sequences containing the characters '(', ')', '\[', and '\]'. You need to find the shortest valid bracket sequence such that the given bracket sequence is a subsequence of it.

### Input Description:
The first line of input is a positive integer, representing the number of data sets. The content of each data set is as described below. After this line, there is a blank line, and there is also a blank line between every two data sets.

Each input set consists of one line, containing at most 100 brackets (characters '(', ')', '\[', and '\]'), without any spaces between the brackets.

### Output Description:
For each data set, the output must meet the following format:

Output the shortest valid bracket sequence that satisfies the problem description, and ensure there is a blank line between every two outputs. Specifically, there must also be a blank line after the last output, meaning the last line is blank.

### Sample Input:
    1
    ([(]
### Sample Output:
    ()[()]

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
