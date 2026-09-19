The currency used in Takahashi Kingdom is Myon. There are 1-, 10-, 100-, 1000- and 10000-Myon coins, and so forth. Formally, there are 10^n-Myon coins for any non-negative integer n.

There are N items being sold at Ex Store. The price of the i-th (1≦i≦N) item is A_i Myon.

Takahashi is going to buy some, at least one, possibly all, of these N items. He hates receiving change, so he wants to bring coins to the store so that he can pay the total price without receiving change, no matter what items he chooses to buy. Also, since coins are heavy, he wants to bring as few coins as possible.

Find the minimum number of coins he must bring to the store. It can be assumed that he has an infinite supply of coins.

Constraints

* 1≦N≦20,000
* 1≦A_i≦10^{12}
Input

The input is given from Standard Input in the following format:


N
A_1 A_2 ... A_N


Output

Print the minimum number of coins Takahashi must bring to the store, so that he can pay the total price without receiving change, no matter what items he chooses to buy.

Examples

Input

3
43 24 37


Output

16


Input

5
49735011221 970534221705 411566391637 760836201000 563515091165


Output

105

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
