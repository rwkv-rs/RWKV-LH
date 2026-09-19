Given some $2 \times 2$ Lego blocks, which are white (W), gray (G), and black (B). You need to place these blocks on a $6 \times 6$ baseplate, ensuring that no blocks are completely floating (i.e., all four squares are empty) and that they do not exceed the $6 \times 6$ baseplate.

You are provided with a schematic of one side of the baseplate after all blocks have been placed, and a schematic of the same side rotated $90^\circ$ counterclockwise. Determine the number of ways to place the blocks.

## Input Format

The first line contains an integer $H$ representing the height of the placement.  
The next $H$ lines each contain six characters, representing the schematic as seen from one side.  
The following $H$ lines each contain six characters, representing the schematic of the same side rotated $90^\circ$ counterclockwise.  
Views are only from the front, back, left, and right sides, not from the top or bottom.

## Output Format

A single line containing an integer representing the answer.  
The answer is guaranteed to fit within a 64-bit signed integer.

## Sample Input and Output

### Sample Input #1

```
2
WWGG..
.BB.WW
.WGG..
WWGG..
```

### Sample Output #1

```
6
```

## Notes

### Sample 1 Explanation

The image below illustrates the sample:

![](https://cdn.luogu.com.cn/upload/image_hosting/njr2rk9l.png)

The first is the schematic observed from side $A$.  
The second is the schematic observed from side $B$ (side $A$ rotated $90^\circ$ counterclockwise).

Below are the six possible configurations (images courtesy of Vonov):

![](https://cdn.luogu.com.cn/upload/image_hosting/wymozlif.png)  
![](https://cdn.luogu.com.cn/upload/image_hosting/1vw0fu3t.png)  
![](https://cdn.luogu.com.cn/upload/image_hosting/umn2hync.png)  
![](https://cdn.luogu.com.cn/upload/image_hosting/pykojvay.png)  
![](https://cdn.luogu.com.cn/upload/image_hosting/9z9wvzxp.png)  
![](https://cdn.luogu.com.cn/upload/image_hosting/hkp3tjfp.png)

### Data Size and Constraints

For $100\%$ of the data, $1 \le H \le 6$.

### Notes

Translated from [BalticOI 2010 Day1 B Lego](https://boi.cses.fi/files/boi2010_day1.pdf).

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
