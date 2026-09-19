Scientists are researching a new type of asexual microorganism (abbreviated as ACM). This unusual ACM can rapidly reproduce itself in large numbers. An ACM's lifecycle comprises three stages:

- Infant Stage: The first few seconds of its birth.
- Splitting Stage: Within a few milliseconds, an ACM can split into a maximum of 100 offspring.
- During its last few moments, it remains inactive.

At the start of the experiment, a newborn ACM is placed in a suitable container as its petri dish. This cell is labeled as 0, and, as it begins to split, its descendants are labeled sequentially as 1, 2, and so on. Throughout the experiment, a special device records the identifier of each ACM. The experiment concludes after a certain amount of time. Your task is to help the scientists determine whether a given ACM is a descendant of another.

## Input and Output Format

### Input:
The first line contains a positive integer T (1 <= T <= 10), representing the number of test cases. Following these T test cases, there is a blank line. 

Next, for each test case, the input starts with a positive integer N (1 <= N <= 300,000), which indicates the number of recorded ACMs. Following this are N numbers i, where the i-th number indicates the identifier of the offspring Ci of ACM i; (0 <= i < N; 0 <= Ci <= 100). The next line contains a positive integer M, representing the number of queries. 

The following M lines each contain two positive integers a and b, inquiring whether ACM a is an ancestor of ACM b.

### Output:
Your output must strictly adhere to the format. The answer to each query should begin with Case #, where # is the query number (starting from 1). A blank line should be printed between the responses to queries. Do not print a blank line after the last query. For each query, output Yes or No, indicating whether ACM a is an ancestor of ACM b.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
