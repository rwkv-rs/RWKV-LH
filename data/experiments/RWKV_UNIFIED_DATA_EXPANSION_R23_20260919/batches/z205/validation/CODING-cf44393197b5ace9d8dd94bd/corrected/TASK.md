Professor Sharma gives the following problem to his students: given two integers X( ≥ 2) and Y( ≥ 2)
 and tells them to find the smallest positive integral exponent E such that the decimal expansion of X^E begins with Y.
For example, if X = 8 and Y= 51, then X^3 = 512 begins with Y= 51, so E= 3. 
Professor Sharma has also announced that he is only interested in values of X such that
X is not a power of 10. The professor has a proof that in this case, at least one value of E exists for any Y.
now your task is to perform professor's theory and check his theory for different values of X and Y .
Input :
The first line contains the number of test cases N(0<N ≤ 9).
For each test case, there is a single line containing the integers X and Y.

Output :
For each test case, print the case number, followed by a space and a  colon, followed by a single space, followed by a single integer showing the value of the smallest exponent E.

Constraints
         1<T<10 
         2<X,Y ≤ 10^5

SAMPLE INPUT
2
5 156
16 40

SAMPLE OUTPUT
Case 1: 6
Case 2: 3

Explanation

Case 1: 
55 = 255 =1255 = 6255 = 3125*5 = 15625 =  6
so after 6 turns we gets our answer cos 156 is present in 15625.

Case 2: 
1616 = 25616 = 4096 = 3
so after 3 turns we gets our answer  cos 40 which is present in 4096

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
