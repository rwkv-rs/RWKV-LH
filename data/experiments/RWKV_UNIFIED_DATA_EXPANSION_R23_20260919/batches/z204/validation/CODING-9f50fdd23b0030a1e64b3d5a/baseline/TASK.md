A project can be divided into several parts, each of which must be completed continuously. For example, if a part requires 3 days, it must be completed over three consecutive days.

There are four types of constraints between the parts:
1. FAS A B means B should be completed after A starts.
2. FAF A B means B should be completed after A is finished.
3. SAF A B means B should start after A is finished.
4. SAS A B means B should start after A starts.

Assuming that any number of parts can be worked on simultaneously, your task is to schedule the start time of each part to minimize the total time.

**Input Description:**

There are several groups of data.

The first line of each group is the total number of parts n. The following n lines each contain an integer ti indicating the time required for the ith part. The subsequent lines each contain a constraint XXX A B, where XXX is one of the four constraints. Each group of input ends with a #.

**Output Description:**

The output should include n lines, each line containing two integers, representing the part number and the start time. The start time should be a non-negative integer, with the first part starting at time 0.

If no solution exists, output a single line containing **impossible**.

**Note:** There should be a blank line after each group of output.

## Input and Output Samples

### Sample Input #1

```
3
2
3
4
SAF 1 2
FAF 2 3
#
3
1
1
1
SAF 1 2
SAF 2 3
SAF 3 1
#
```

### Sample Output #1

```
Case 1:
1 0
2 2
3 1

Case 2:
impossible
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
