I love tranquility, you adore noise; I am loyal to warmth, you are fond of coolness.

If everything has an opposite, what about the colors that stitch our world?

Is it just black and white?

## Problem Description

To formally describe colors, we introduce **RGB color values**, represented by a triplet \((r, g, b)\), where \(r, g, b\) are the **R value**, **G value**, and **B value** of the color, respectively, satisfying \(0 \le r, g, b \le 255\) and all being **decimal integers**.

Clearly, this color system can represent \(256 \times 256 \times 256 = 16,777,216\) different colors. For a color \((r, g, b)\), its **complementary color** is defined as \((255-r, 255-g, 255-b)\).

However, people found that using RGB color values is inconvenient, as copying a color requires copying three values.

Thus, **hexadecimal color codes** were born, which are strings of length 7 like `#EBA932`. Specifically:

- The first character of the string is `#`, serving as the color code identifier.
- The second and third characters are hexadecimal digits, forming a hexadecimal number equal to the R value in decimal.
- The fourth and fifth characters are hexadecimal digits, forming a hexadecimal number equal to the G value in decimal.
- The sixth and seventh characters are hexadecimal digits, forming a hexadecimal number equal to the B value in decimal.

**Hexadecimal digits** range from `0` to `F`, including `0`, `1`, `2`, `3`, `4`, `5`, `6`, `7`, `8`, `9`, `A`, `B`, `C`, `D`, `E`, `F`, with `A`, `B`, `C`, `D`, `E`, `F` being **uppercase**.

Now, you are given a hexadecimal color code. Please output its complementary color in hexadecimal color code format.

*Hint: RGB values and hexadecimal codes can be converted to each other (refer to Sample Explanation #2)*

## Input Format

A single line of input, a string of length 7 representing the original color in hexadecimal color code.

## Output Format

A single line of output, a string of length 7 representing the complementary color in hexadecimal color code.

## Sample Input and Output

### Sample Input #1

```
#FFFFFF
```

### Sample Output #1

```
#000000
```

### Sample Input #2

```
#EBA932
```

### Sample Output #2

```
#1456CD
```

## Notes

**[Sample Explanation #1]**

The RGB values of the original color are \((255, 255, 255)\), and the RGB values of the complementary color are \((0, 0, 0)\), corresponding to the hexadecimal code `#000000`.

**[Sample Explanation #2]**

The RGB values of the original color are \((235, 169, 50)\), and the RGB values of the complementary color are \((20, 86, 205)\), corresponding to the hexadecimal code `#1456CD`.

To avoid misunderstandings, here is a special explanation for why the B value of `#EBA932` is 50 after conversion: Extract the sixth and seventh characters of the string, forming the hexadecimal number \((32)_{16}\), which equals \(3 \times 16^1 + 2 \times 16^0 = 50\).

---

**[Data Range and Constraints]**

There are 10 test cases in total, and passing each test case earns 10 points.

For 10% of the data, it is Sample #1.

For another 30% of the data, neither the input nor the output strings contain uppercase letters.

For all data, the given string is guaranteed to be a valid hexadecimal color code.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
