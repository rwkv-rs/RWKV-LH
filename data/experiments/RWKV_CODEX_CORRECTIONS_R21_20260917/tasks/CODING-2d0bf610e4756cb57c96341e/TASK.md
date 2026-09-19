There is a game called Sim Forest 2013. In this game, the player can become a forest god and raise forest animals.

Animals hatch from eggs and breed. When certain conditions are met, eggs are mutated with a certain probability to give birth to new races of animals.

There is an animal encyclopedia in this game, and when you get a new kind of animal, it will be recorded in the animal dictionary.

Mori is an enthusiastic player of Sim Forest 2013. His animal dictionary is complete when the remaining one race is filled.

Mori decided to obtain this remaining one race by mutation from the egg.

The game progress is as follows.

* N eggs will appear at the beginning of the stage.
* N eggs hatch s minutes after the start of the stage.
* Each egg has a 1 / p chance of targeting on a specific day of the week and within a specific time zone during the entire period * from appearance to hatching * (including the time of appearance and the moment of hatching). Mutates in animals.
* The stage ends t minutes after the start of the stage, and the same stage starts immediately after that (starts with n eggs. The elapsed time is not reset).
* The stage is repeated m times in a row.



This game meets the following specifications.

* Animals born from eggs do not lay eggs.
* Eggs hatch only once per stage, s minutes after the start of the stage.
* Mr. Sori can set the start day and start time of the first stage as desired. (The start time of the second and subsequent stages will be immediately after the end of the previous stage)
* One of {all days, Sunday, Monday, Tuesday, Wednesday, Thursday, Friday, Saturday} is given as a mutable day.
* One of {all time zones, morning, night} is given as a mutable time zone.
Inputs are s, n, t, mutable day / time zone, p, m. Find the probability when you set the start day and start time of the first stage so that the probability of mutation occurring by the end of all stages is maximized.

Input

The input consists of multiple datasets. Each dataset is given in the following format:


s n t weekday time p m


Each dataset shows the time it takes for an egg to hatch from the start of the stage s, the number of eggs that appear at the start of the stage n, the time it takes to finish one stage t, the mutable day weekday, the mutable Time zone time, reciprocal of mutation probability p (mutation probability is 1 / p), total number of stages m.

The input satisfies the following constraints.

* 0 <s <= 500
* 0 <n <= 100
* s <t <= 1000
* weekday ∈ {All, Sun, Mon, Tue, Wed, Thu, Fri, Sat}
* All means all days of the week
* time ∈ {All, Day, Night}
* All means [0: 00 ~ 24: 00), Day means [6: 00 ~ 18: 00), and Night means [18: 00 ~ 6: 00).
* 1 <= p <= 99999
* 1 <= m <= 100



The end of the input is given on the following line.


0 0 0 None None 0 0


Output

For each dataset, output the probability when the start day and start time of the first stage is set so that the probability of mutation occurring by the end of all stages is maximized. The error in the answer must not exceed 0.00000001 (10-8). Any number of digits after the decimal point may be output as long as the precision conditions are met.

Sample Input


1 1 3 All All 1 1
2 37 5 All Night 150 1
16 2 20 All Day 5 10
1 14 15 Mon All 20000 100
0 0 0 None None 0 0


Output for Sample Input


1.0000000000
0.2192439716
0.9884707850
0.0649933899






Example

Input

1 1 3 All All 1 1
2 37 5 All Night 150 1
16 2 20 All Day 5 10
1 14 15 Mon All 20000 100
0 0 0 None None 0 0


Output

1.0000000000
0.2192439716
0.9884707850
0.0649933899

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
