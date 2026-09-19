In the field of commercial aircraft manufacturing, Boeing and Airbus are the two major manufacturers. Boeing's airplanes have two engines, while Airbus has four. However, this does not imply that Airbus planes are safer than Boeing's. Both companies are trying to enhance their products as much as possible, but this doesn't resolve the issue.

Regarding twin-engine aircraft and four-engine aircraft, here are some interesting facts. Many people say that in order for an aircraft to stay safely airborne, at least 50% of the engines must be operational. In this problem (UVA11864), we assume this statement is correct. Thus, if an aircraft has 5 engines, at least 3 engines must be operational for a safe flight. If all engines have an equal probability $p$ of remaining operational, but failures are independent, we can use the binomial theorem to calculate the probability of a successful flight. For instance, an aircraft with 5 engines has a flight success probability calculated as follows:

![](https://cdn.luogu.org/upload/pic/64623.png)

Similarly,

![Image Placeholder](https://gitee.com/OKB-156/okb-design-pics/raw/master/%E6%9D%82%E5%9B%BE/2.PNG)

Additionally, we define the function $CF$:

![Image Placeholder](https://gitee.com/OKB-156/okb-design-pics/raw/master/%E6%9D%82%E5%9B%BE/3.PNG)

Nowadays, it is rare to see aircraft with more than four engines. However, scientists are planning to develop aircraft equipped with thousands of small engines. The reasoning is as follows:
1. The probabilities calculated above correspond to real-life situations when the number of items is significantly large. For example, the probability of a coin landing heads up is 0.5. However, in real life, flipping a coin ten times may not yield five heads. But if we flip it 10,000 times, the number of heads will be approximately 5,000.
2. Generally, designing an engine that never fails is much more expensive than creating an engine with a very low operational probability $p$ (e.g., 0.6). Therefore, if an aircraft has 10,000 engines, in real-world situations, the probability that 50% of the engines cannot operate is very low even if $p$ is around 0.6.

In this problem (UVA11864), your task is to help scientists find the value of the $CF$ function given $m$ and $p$. Scientists have said these values are very useful for their research.

## Input Format
The input file contains approximately 12 sets of data. Below is the description for each set:

The first line contains a floating-point number $p$ ($0 \leq p \leq 1$) and an integer $Q$ ($0 \leq Q \leq 2000$).

Here, $p$ refers to the probability that an engine **does not** fail, and $Q$ refers to the total number of queries.

The following $Q$ lines each contain an integer $m$ ($0 \leq m \leq 50001$).

When $Q$ is 0, the input ends.

## Output Format
For each group of $Q+1$ lines of input, the first line should contain the continuous case number (index). The next $Q$ lines should each contain a floating-point number representing the value of the $CF(m)$ function. These floating-point numbers should have 8 decimal places. The allowed maximum error range is:

![Error Tolerance](https://gitee.com/OKB-156/okb-design-pics/raw/master/%E6%9D%82%E5%9B%BE/4.PNG)

You can also refer to the sample output details.

## Sample Input

```
0.9 3
10
11
12
0.1 3
100
20
30
0.4 0
```

## Sample Output

```
Case 1:
9.84427253
10.84397682
11.84392664
Case 2:
0.40625000
0.40624417
0.40624997
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
