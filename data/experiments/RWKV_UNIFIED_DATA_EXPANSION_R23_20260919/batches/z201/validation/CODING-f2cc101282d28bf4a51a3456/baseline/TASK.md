In May 3206, Dr. Liu's OI team, specializing in ET studies, discovered that Earth was being attacked by extraterrestrial biobeings. These biobeings used a highly secretive multiplication encryption to control arsenals equipped with massive weapons, occupied numerous cities, and even initiated the K-bomb plan...

Dr. Liu's OI team decided to leverage their research institution's capabilities (due to the unique geographical advantage of Jilin Province, this institution is the only one globally located in Jilin) to subdue these extraterrestrial biobeings. They managed to capture several of these biobeings and, after studying them, found that their survival on Earth depends on a parameter: the survival degree. Their task is to find the maximum value of this parameter. Thus, they began their research on the growth of these extraterrestrial biobeings.

Before each experiment, they randomly place an extraterrestrial biobeing's cells in one grid of an N*N square cultivation container and label each grid with a value representing the survival degree of the biobeing in that cell (which can be positive or negative, with larger values indicating greater danger). The survival degree of the entire biobeing is the sum of the survival degrees of all the grids it occupies. During each experiment, the biobeing naturally grows. The biobeing chooses a part of its body (a grid) every unit time and randomly grows into an adjacent empty grid with a common edge. For example, in one experiment, the biobeing initially occupies only one grid and then begins to grow:

![](https://cdn.luogu.com.cn/upload/pic/6844.png)

Dr. Liu's OI team conducted numerous experiments and recorded and statistically analyzed the data. Assuming that the number of experiments conducted is sufficient, what is the maximum survival degree the biobeing can achieve at a certain moment during the experiments?

In September 3206, the extraterrestrial biobeings, who sought to destroy Earth, were finally subdued by Dr. Liu's OI team...

## Input Format

The first line of the input file includes a positive integer N, representing the side length of the experimental container.

The next N lines, each containing N integers separated by spaces, represent the survival degree of the extraterrestrial biobeing in each grid.

## Output Format

Output a single line representing the maximum survival degree the biobeing achieved during the experiments.

## Sample Input and Output

### Input Sample #1

```
4
2 -1 -1 -1
5 -5 -1 -5
3  2 -1  3
2 -2 -3  2
```

### Output Sample #1

```
18
```

## Notes/Hints

For 40% of the data, N <= 6.

For 100% of the data, N <= 9.

The absolute value of the survival degree in each grid does not exceed 32767.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
