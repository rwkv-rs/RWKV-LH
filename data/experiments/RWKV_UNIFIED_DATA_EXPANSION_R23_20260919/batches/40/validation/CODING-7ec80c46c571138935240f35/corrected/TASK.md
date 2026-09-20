In a magical forest, there lives a clever cat named Congcong and a cute mouse named Coco. Despite Cinderella's fondness for them, Congcong is, after all, a cat, and Coco is, after all, a mouse. What remains constant is Congcong's desire to eat Coco.

One day, Congcong accidentally obtained a very useful machine, said to be a GPS, which can accurately locate Coco. With this machine, Congcong finds it easy to catch Coco. Therefore, Congcong is ready to set out immediately to find Coco. Poor Coco, unaware of the impending disaster, is still carefreely playing in the forest. The obedient little rabbit heard about this and immediately reported it to Cinderella. Cinderella decided to stop Congcong as soon as possible to save Coco, but she is unsure if there is enough time.

The entire forest can be considered as an undirected graph with $N$ beautiful scenic spots, numbered from $1$ to $N$. The animals only rest and play at these scenic spots. There are some paths connecting the spots.

When Congcong gets the GPS, Coco is at scenic spot $M$ ($M \le N$). In each time unit, Coco may choose to move to one of the adjacent spots or stay at the current spot, with equal probability. Suppose there are $P$ spots adjacent to spot $M$, namely spots $R$, $S$, ..., $Q$. At time $T$, if Coco is at spot $M$, then at time $(T+1)$, Coco has a $1/(1 + P)$ chance to be at spot $R$, a $1/(1 + P)$ chance to be at spot $S$, ..., a $1/(1 + P)$ chance to be at spot $Q$, and a $1/(1 + P)$ chance to remain at spot $M$.

We know that Congcong is very smart. When she is at spot $C$, she will choose a spot closer to Coco. If there are multiple such spots, she will choose the one with the smallest number. Because Congcong is so eager to catch Coco, if she hasn't caught Coco after the first move, she can move closer to Coco again within the same time unit.

In each time unit, assuming Congcong moves first and Coco moves later. At any moment, if Congcong and Coco are at the same spot, poor Coco gets eaten.

Cinderella wants to know, on average, how many steps Congcong might take to catch Coco. You need to help Cinderella find the answer as quickly as possible.

## Input Format

The first line of the data contains two integers $N$ and $E$, separated by a space, representing the number of scenic spots in the forest and the number of paths connecting adjacent spots, respectively.

The second line contains two integers $C$ and $M$, separated by a space, representing the initial positions of Congcong and Coco, respectively.

The next $E$ lines, each containing two integers, describe the paths. The $(i+2)$-th line contains two integers $A_i$ and $B_i$, indicating that there is a path between scenic spot $A_i$ and scenic spot $B_i$. All paths are undirected, meaning if one can go from $A$ to $B$, one can also go from $B$ to $A$.

The input guarantees that there is no more than one direct path between any two spots, and there is a direct or indirect path between Congcong and Coco.

## Output Format

Output a single real number, rounded to three decimal places, indicating the average number of time units it takes for Congcong to catch Coco.

## Sample Input and Output

### Input Sample #1

```
4 3 
1 4 
1 2 
2 3 
3 4
```

### Output Sample #1

```
1.500 
```

### Input Sample #2

```
9 9 
9 3 
1 2 
2 3 
3 4 
4 5 
3 6 
4 6 
4 7 
7 8 
8 9
```

### Output Sample #2

```
2.167
```

## Notes/Hints

**Sample Explanation 1**

Initially, Congcong and Coco are at spots 1 and 4, respectively.

In the first moment, Congcong moves first, heading towards a spot closer to Coco (spot 4), moving to spot 2, then to spot 3; assuming no time is spent on walking.

Coco moves later, with two possibilities:
- First, moving to spot 3, where Congcong and Coco meet, resulting in Coco being eaten in 1 step, with a probability of $0.5$.
- Second, staying at spot 4, not being eaten, with a probability of $0.5$.

In the second moment, Congcong moves closer to Coco (spot 4) with just one step, meeting Coco. Thus, in this case, Congcong catches Coco in two steps. Therefore, the average number of steps is $1 \times 1/2 + 2 \times 1/2 = 1.5$.

**Sample Explanation 2**

The forest is depicted as follows:

![](https://cdn.luogu.com.cn/upload/image_hosting/8uiq0ltc.png)

For 50% of the data, $1 \le N \le 50$.
For all data, $1 \le N, E \le 1000$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
