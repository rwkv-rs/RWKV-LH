### Problem Description

The Mandelbrot set, named after Benoit Mandelbrot, is a fractal.

The Mandelbrot set is a collection of complex numbers, where a complex number is a number in the form of $a+b\sqrt{-1}$, and we denote $i=\sqrt{-1}$, thus allowing us to express the number as $a+bi$, such as $2.5+3i$. Given that $i^2=-1$, we can deduce $(3i)^2=9\times -1=-9$.

Unfortunately, we cannot place $i$ on the real number axis, so we place it on the imaginary axis, giving us a complex plane, with the imaginary axis perpendicular to the real axis, as shown:

![Complex Plane](https://cdn.luogu.com.cn/upload/image_hosting/nq1ppyjd.png)

The plane marks a number $1+2i$.

The Mandelbrot set consists of complex numbers that are plotted on the complex plane, and we determine if a complex number is in the set using the equation $f(z)=z^2+C$, then updating $z \leftarrow f(z)$, where the constant $C$ is the number we need to determine. Initially, $z$ is $0+0i$, and we compute $f(z)$ using $C$ and assign it to $z$.

We monitor the magnitude $||z||=\sqrt{(\Re z)^2+(\Im z)^2}$ rather than how $z$ changes. If $||z||$ ever exceeds $2$, it will keep expanding and will not decrease again, indicating it does not belong to the Mandelbrot set.

Testing as many complex numbers as possible results in an image like this:

![Mandelbrot Set](https://cdn.luogu.com.cn/upload/image_hosting/neqchaaf.png)

Elements outside the Mandelbrot set can be colored, with the color indicating the iterations needed for their magnitude to exceed $2$.

To appreciate the beauty of the Mandelbrot set, simply magnify the image.

Your task: Given a range of values, render the described set using ASCII art.

### Input Format

$T$ datasets, each contains the following:

+ String $C$, which starts and ends with quotation marks, and its content (excluding quotation marks) is of length $12$.
+ Two real numbers $\min_\Im$ and $\max_\Im$, representing the imaginary part range $[\min_\Im,\max_\Im]$.
+ Two real numbers $\min_\Re$ and $\max_\Re$, representing the real part range $[\min_\Re,\max_\Re]$.
+ Two real numbers $\mathrm{prec}_\Im$ and $\mathrm{prec}_\Re$, indicating the precision for the real and imaginary parts per character.

The input sequence is: $C,\min_\Im,\max_\Im,\mathrm{prec}_\Im,\min_\Re,\max_\Re,\mathrm{prec}_\Re$.

## Output Format

Produce an ASCII representation as follows:

```plaintext
[MINI+0*PRECI,MINR+0*PRECR] [MINI+0*PRECI,MINR+1*PRECR] [MINI+0*PRECI,MINR+2*PRECR] (...) [MINI+0*PRECI,B]
[MINI+1*PRECI,MINR+0*PRECR] [MINI+1*PRECI,MINR+1*PRECR] [MINI+1*PRECI,MINR+2*PRECR] (...) [MINI+1*PRECI,B]
[MINI+2*PRECI,MINR+0*PRECR] [MINI+2*PRECI,MINR+1*PRECR] [MINI+2*PRECI,MINR+2*PRECR] (...) [MINI+2*PRECI,B]
(...)                       (...)                       (...)                       (...) (...)
[           A,MINR+0*PRECR] [           A,MINR+1*PRECR] [           A,MINR+2*PRECR] (...) [           A,B]
```

Each bracket denotes a complex number, where $A,B$ are the largest numbers less than or equal to $\max_\Im,\max_\Re$.

If a complex number's magnitude exceeds $2$, use the $i^{th}$ character from $C$ for annotation, where $i$ is the iteration it first exceeds $2$. If it never exceeds $2$, place a space.

Output the image as shown, separated by a blank line.

## Sample Input

### Input Sample #1

```
2
"#$&/|[]+;:-." -1.2 1.2 0.1 -2 1 0.05
"1234567890AB" -1.2 -0.8 0.02 -0.5 0.5 0.02
```

### Output Sample #1

```
########$$$$$$$$$$&&&&&&&&&&&&&&&&&&&&&&&&&$$$$$$$$$$$$$$$$$$
#######$$$$$$$&&&&&&&&&&&&&&&&/////| +||///&&&&$$$$$$$$$$$$$$
######$$$$$&&&&&&&&&&&&&&&&//////||[]-;- |////&&&&$$$$$$$$$$$
#####$$$&&&&&&&&&&&&&&&&///////|||[+; -+[||////&&&&&$$$$$$$$
####$$&&&&&&&&&&&&&&&&///////||[[]+
+[||||//&&&&&&$$$$$$
###$$&&&&&&&&&&&&&&//////||[]++++;:
:;+[[[ |//&&&&&$$$$$
##$$&&&&&&&&&&&&&////||||[[].
.
|/&&&&&&$$$$
##$&&&&&&&&&&&//|||||||[[[+ .
][|/&&&&&&$$$
#$&&&&&&&///||].]]]]]]]]]+-
; |//&&&&&&$$
#&&&//////|||[]: .
-;;-
+[//&&&&&&&$
#&//////||||[]+-
]|///&&&&&&$
#/////[[[[]+.
+[|///&&&&&&$
.+][|///&&&&&&&
#/////[[[[]+.
+[|///&&&&&&$
#&//////||||[]+-
]|///&&&&&&$
#&&&//////|||[]: .
-;;-
+[//&&&&&&&$
#$&&&&&&&///||].]]]]]]]]]+-
; |//&&&&&&$$
##$&&&&&&&&&&&//|||||||[[[+ .
][|/&&&&&&$$$
##$$&&&&&&&&&&&&&////||||[[].
.
|/&&&&&&$$$$
###$$&&&&&&&&&&&&&&//////||[]++++;:
:;+[[[ |//&&&&&$$$$$
####$$&&&&&&&&&&&&&&&&///////||[[]+
+[||||//&&&&&&$$$$$$
#####$$$&&&&&&&&&&&&&&&&///////|||[+; -+[||////&&&&&$$$$$$$$
######$$$$$&&&&&&&&&&&&&&&&//////||[]-;- |////&&&&$$$$$$$$$$$
#######$$$$$$$&&&&&&&&&&&&&&&&/////| +||///&&&&$$$$$$$$$$$$$$
########$$$$$$$$$$&&&&&&&&&&&&&&&&&&&&&&&&&$$$$$$$$$$$$$$$$$$
333333333333333333333333333333333222222222222222222
333333333333334444433333333333333332222222222222222
333333334444444444444444433333333333322222222222222
333334444444445555555444444433333333333222222222222
334444444444558866555554444444433333333332222222222
444444444445567 9B755555444444444333333333322222222
4444444444555678B9766555544444444433333333332222222
4444444445555668A0866666554444444444333333333322222
44444444555556670 A87667765444444444433333333332222
4444444555556667
08778A75544444444443333333333322
444444555555666790 99AA 6554444444444333333333332
444444555555667889 B
A76654444444444433333333333
444445555555677889A
A9876655444444444443333333333
444455555556677880A B09876655544444444444333333333
44455555556677889A
A9877655554444444444433333333
4455555556677899
9887665555544444444443333333
4555555566789 0AB
0988765555554444444444333333
555555566680B
AAB 866555555444444444433333
5555566667A
B876555555554444444433333
55566666789AB
A76655555555444444443333
566666677880B
B977665555555554444444333
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
