DotR (Defense of the Robots) Allstars is a globally popular Warcraft map, with rules that are simple and similar to the equally popular map DotA (Defense of the Ancients) Allstars.

In DotR, heroes have only one attribute—strength. They need to purchase equipment to increase their strength value. Each piece of equipment increases the strength value of the hero who wears it by a fixed amount. Therefore, a hero's strength value is the sum of the strength values of all the equipment they have purchased. Equipment is divided into basic and advanced types. Basic equipment can be bought directly from the store with gold coins, while advanced equipment requires basic equipment or lower-level advanced equipment for synthesis, which does not require additional gold coins. The synthesis route of equipment can be represented by a tree.

For example, the synthesis of Sange and Yasha requires Sange, Yasha, and Sange and Yasha Recipe Scroll. Sange, in turn, is synthesized using Ogre Axe, Belt of Giant Strength, and Sange Recipe Scroll. Each basic piece of equipment has a quantity limit, which restricts the unlimited synthesis of some cost-effective equipment.

Now, the hero Spectre has M gold coins and wants to use this money to purchase equipment to maximize his strength value. Can you help him with this? In return, he will teach you the magic Haunt (Ghost Possession).

## Input Format

The first line contains two integers, N (1 <= N <= 51) and M (0 <= M <= 2,000), representing the number of types of equipment and the number of gold coins, respectively. Equipment is numbered from 1 to N.

The next N lines, in the order of equipment 1 to equipment N, describe each piece of equipment.

The first non-negative integer on each line represents the strength value contributed by this equipment.

The following non-empty character indicates whether this equipment is basic or advanced. 'A' denotes advanced equipment, and 'B' denotes basic equipment. If it is basic equipment, the next two positive integers represent its unit price (in gold coins) and quantity limit (not exceeding 100), respectively. If it is advanced equipment, the next positive integer C indicates that this advanced equipment requires C types of lower-level equipment. The following 2C numbers describe the type and quantity required for each lower-level equipment.

## Output Format

The first line contains an integer S, representing the maximum strength value that can be increased.

## Sample Input and Output

### Input Sample #1

```
10 59
5 A 3 6 1 9 2 10 1
1 B 5 3
1 B 4 3
1 B 2 3
8 A 3 2 1 3 1 7 1
1 B 5 3
5 B 3 3
15 A 3 1 1 5 1 4 1
1 B 3 5
1 B 4 3
```

### Output Sample #1

```
33
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
