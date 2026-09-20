500-yen Saving

"500-yen Saving" is one of Japanese famous methods to save money. The method is quite simple; whenever you receive a 500-yen coin in your change of shopping, put the coin to your 500-yen saving box. Typically, you will find more than one million yen in your saving box in ten years.

Some Japanese people are addicted to the 500-yen saving. They try their best to collect 500-yen coins efficiently by using 1000-yen bills and some coins effectively in their purchasing. For example, you will give 1320 yen (one 1000-yen bill, three 100-yen coins and two 10-yen coins) to pay 817 yen, to receive one 500-yen coin (and three 1-yen coins) in the change.

A friend of yours is one of these 500-yen saving addicts. He is planning a sightseeing trip and wants to visit a number of souvenir shops along his way. He will visit souvenir shops one by one according to the trip plan. Every souvenir shop sells only one kind of souvenir goods, and he has the complete list of their prices. He wants to collect as many 500-yen coins as possible through buying at most one souvenir from a shop. On his departure, he will start with sufficiently many 1000-yen bills and no coins at all. The order of shops to visit cannot be changed. As far as he can collect the same number of 500-yen coins, he wants to cut his expenses as much as possible.

Let's say that he is visiting shops with their souvenir prices of 800 yen, 700 yen, 1600 yen, and 600 yen, in this order. He can collect at most two 500-yen coins spending 2900 yen, the least expenses to collect two 500-yen coins, in this case. After skipping the first shop, the way of spending 700-yen at the second shop is by handing over a 1000-yen bill and receiving three 100-yen coins. In the next shop, handing over one of these 100-yen coins and two 1000-yen bills for buying a 1600-yen souvenir will make him receive one 500-yen coin. In almost the same way, he can obtain another 500-yen coin at the last shop. He can also collect two 500-yen coins buying at the first shop, but his total expenditure will be at least 3000 yen because he needs to buy both the 1600-yen and 600-yen souvenirs in this case.

You are asked to make a program to help his collecting 500-yen coins during the trip. Receiving souvenirs' prices listed in the order of visiting the shops, your program is to find the maximum number of 500-yen coins that he can collect during his trip, and the minimum expenses needed for that number of 500-yen coins.

For shopping, he can use an arbitrary number of 1-yen, 5-yen, 10-yen, 50-yen, and 100-yen coins he has, and arbitrarily many 1000-yen bills. The shop always returns the exact change, i.e., the difference between the amount he hands over and the price of the souvenir. The shop has sufficient stock of coins and the change is always composed of the smallest possible number of 1-yen, 5-yen, 10-yen, 50-yen, 100-yen, and 500-yen coins and 1000-yen bills. He may use more money than the price of the souvenir, even if he can put the exact money, to obtain desired coins as change; buying a souvenir of 1000 yen, he can hand over one 1000-yen bill and five 100-yen coins and receive a 500-yen coin. Note that using too many coins does no good; handing over ten 100-yen coins and a 1000-yen bill for a souvenir of 1000 yen, he will receive a 1000-yen bill as the change, not two 500-yen coins.
Input

The input consists of at most 50 datasets, each in the following format.

> n
>  p1
>  ...
>  pn
>

n is the number of souvenir shops, which is a positive integer not greater than 100. pi is the price of the souvenir of the i-th souvenir shop. pi is a positive integer not greater than 5000.

The end of the input is indicated by a line with a single zero.

Output

For each dataset, print a line containing two integers c and s separated by a space. Here, c is the maximum number of 500-yen coins that he can get during his trip, and s is the minimum expenses that he need to pay to get c 500-yen coins.

Sample Input


4
800
700
1600
600
4
300
700
1600
600
4
300
700
1600
650
3
1000
2000
500
3
250
250
1000
4
1251
667
876
299
0


Output for the Sample Input


2 2900
3 2500
3 3250
1 500
3 1500
3 2217






Example

Input

4
800
700
1600
600
4
300
700
1600
600
4
300
700
1600
650
3
1000
2000
500
3
250
250
1000
4
1251
667
876
299
0


Output

2 2900
3 2500
3 3250
1 500
3 1500
3 2217

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
