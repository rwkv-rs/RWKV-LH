In Warcraft III, strategic resources are collected using units such as peasants, peons, wisps, and monks.

In the development of Warcraft IV, Blizzard Entertainment felt that this model was too simplistic, so they wanted to add more units to enrich the collection modes.

In the new mode, players can build various types of "peons," each with different work efficiencies and resource costs for their production.

Blizzard is renowned for its pursuit of balance, so to test the balance of this new mode, they devised a method: measuring the time to reach a certain resource quantity with equal starting resources for all races. If the times are the same, the design can be considered balanced.

They have provided you with the data and hope you can determine if the design is balanced.

## Input Format

The first line contains three numbers, N, M, and T, representing the types of peons, the initial amount of resources, and the target amount of resources, respectively.

The next N lines each contain two numbers, A and B, representing the resources required to produce this type of peon and the efficiency of the peon, which is the amount of resources produced per unit time.

## Output Format

A single number indicating the minimum time to reach the target amount of resources.

Note: Unlike Warcraft III, in Warcraft IV, producing peons does not require time. Also, resource collection is not continuous; that is, if a peon's efficiency is 2, it will harvest 2 units of resources at time 1, and will not harvest 1 unit at time 0.5.

## Sample Input and Output

### Sample Input #1

```
1 1 8
1 1
```

### Sample Output #1

```
4
```

### Sample Input #2

```
2 1 8
1 1
2 8
```

### Sample Output #2

```
3
```

## Notes

For 30% of the data, N <= 10, M, T <= 300.

For 100% of the data, N <= 100, M, T <= 1000, A, B <= 2^31.

The data guarantees a solution.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
