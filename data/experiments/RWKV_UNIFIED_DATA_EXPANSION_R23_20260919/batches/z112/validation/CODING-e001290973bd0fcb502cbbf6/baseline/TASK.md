D: Anipero 2012

Anipero Summer Live, commonly known as Anipero, is the largest anime song live event in Japan where various anime song artists gather. 2D, who loves anime songs, decided to go to Anipero this year as well as last year.

He has already purchased m of psyllium to enjoy Anipero. Psyllium is a stick that glows in a chemical reaction when folded. By shaking the psyllium in time with the rhythm, you can liven up the live performance and increase your satisfaction. All the psylliums he purchased this time have the following properties.

* The psyllium becomes darker as time passes after it is folded, and loses its light in 10 minutes.
* Very bright for 5 minutes after folding (hereinafter referred to as "level 2").
* It will be a little dark 5 minutes after folding (hereinafter referred to as "level 1").
* The speed at which light is lost does not change whether it is shaken or not.



2D decided to consider the following problems as to how satisfied he would be with this year's Anipero by properly using the limited psyllium depending on the song.

He anticipates n songs that will be played during the live. The length of each song is 5 minutes. n songs continue to flow, and the interval between songs can be considered as 0 minutes. The following three parameters are given to each song.

* Satisfaction that increases when only one level 2 is shaken for a certain song
* Satisfaction that increases when only one level 1 is shaken for a certain song
* Satisfaction increases when no song is shaken in a certain song



Shaking the glow stick does not necessarily increase satisfaction. If you shake it, it may disturb the atmosphere of the venue and reduce your satisfaction. The same can be said when not shaking.

Psyllium must be used according to the following rules.

* You can fold only when the song starts, and you can fold as many as you like at one time. The time it takes to fold the psyllium can be ignored.
* Up to 8 songs can be played at the same time in one song.
* When shaking multiple psylliums, calculate the satisfaction level to be added by the following formula.
* (Number of Level 1) x (Satisfaction per level 1) + (Number of Level 2) x (Satisfaction per Level 2)
* If no psyllium is shaken, only the satisfaction level when no one is shaken is added.
* Once you decide to shake the psyllium, you cannot change it until the end of one song.
* The psyllium can be left unshaken. Also, it is not necessary to use up all the psyllium.



2D had finished predicting the live song, but he was tired of it and didn't feel like solving the problem. Your job is to write a program for him that seeks the maximum satisfaction you're likely to get at this year's live concert.
Input

Satisfaction information for the expected song list of the live is input.

On the first line, the number of songs n (1 <= n <= 50) sung live and the number m (0 <= m <= 50) of new psyllium that 2D has at the start of the live are separated by spaces. Is entered in. In the following n lines, the information of one song is input line by line. The i-th (1 <= i <= n) song information is

* Satisfaction level when one level 2 psyllium is shaken for song i ai
* Satisfaction level bi when swinging one level 1 psyllium for song i
* Satisfaction ci when no psyllium is shaken in song i



Are entered separated by spaces (-100 <= ai, bi, ci <= 100).

Output

Output the prediction of 2D's maximum satisfaction at the end of the live in one line. Please note that the maximum satisfaction level may be negative. Output a line break at the end of the line.

Sample Input 1


1 5
2 3 8


Sample Output 1


Ten


Sample Input 2


2 10
2 2 20
2 3 -10


Sample Output 2


44


Sample Input 3


3 10
5 1 9
-3 2 1
1 11 0


Sample Output 3


102






Example

Input

1 5
2 3 8


Output

10

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
