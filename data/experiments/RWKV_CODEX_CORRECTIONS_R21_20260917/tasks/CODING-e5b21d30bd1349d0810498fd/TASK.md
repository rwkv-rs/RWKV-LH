ftiasch has $n$ items with volumes $w_1, w_2, \dots, w_n$. Due to her negligence, the $i$-th item is lost.

"How many ways are there to fill a backpack of volume $x$ using the remaining $n-1$ items?" — This is a classic problem.

She records the answer as $\text{cnt}(i, x)$ and wants to obtain the table of $\text{cnt}(i, x)$ for all $i \in [1, n]$ and $x \in [1, m]$.

## Input Format

The first line contains two integers $n$ and $m$, representing the number of items and the maximum volume, respectively.
The second line contains $n$ integers $w_1, w_2, \dots, w_n$, representing the volume of each item.

## Output Format

Output an $n \times m$ matrix, representing the **last digit** of $\text{cnt}(i, x)$.

## Sample Input and Output

### Input Sample #1

```
3 2
1 1 2
```

### Output Sample #1

```
11
11
21
```

## Notes

**Data Range:**
For $100\%$ of the data, $1 \le n, m \le 2000$, and $1 \le v_i \le m$.

**Sample Explanation:**
If item 3 is lost, there is only one way to fill a backpack of volume 2, which is by choosing item 1 and item 2.

---

**upd 2023.8.11:** Added five new Hack data sets.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
