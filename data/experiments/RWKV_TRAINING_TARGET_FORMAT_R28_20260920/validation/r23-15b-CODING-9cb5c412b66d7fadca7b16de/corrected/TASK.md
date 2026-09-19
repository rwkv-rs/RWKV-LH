`Mark-up` is a computer language that supports formatted text (similar to Markdown). Certain keywords (like escape characters in C++, such as `\n`) are used to tag text, allowing for changes in font, page style, paragraph style, etc.

Languages like $\TeX$, HTML, and Troff text editing software all use `Mark-up` languages.

To properly check spelling syntax, a spell checker requires preprocessing to remove keywords.

## Problem Description

You need to create a program to perform keyword removal for a small subset of `Mark-up`. Your program should output "clean text," i.e., the processed string.

This subset of `Mark-up` contains five types of keywords, each starting with a backslash `\`. If a `\` is not followed by a valid keyword, it should be treated as a regular character (i.e., the `\` character should be kept, which is different than in C++). Here are the five keywords:
> `\b` toggles **bold** on or off, default is off;
> 
> `\i` toggles *italic* on or off, default is off;
> 
> `\s` sets font size, `s` can be *optionally* followed by a number; if no number is given, it reverts to the last size set by `\s`; numbers may include decimals, such as `.5` or `3.`.
> 
> `\*` toggles `Mark-up` mode on or off, default is on, when off all text is considered non-keyword (except `\*` itself) and won't be processed as keywords;
> 
> `\\` is used to output a `\` character. 

## Input Format

Any number of lines, representing the raw string input.

## Output Format

The same number of lines as the input, representing the clean text.

## Sample Input #1

```
\s18.\bMARKUP sample\b\s
\*For bold statements use the \b command.\*
If you wish to \iemphasize\i something use the \\i command.
For titles use \s14BIG\s font sizes, 14 points usually works well.
Remember that all of the commands toggle except for the \\s command.
```

## Sample Output #1

```
MARKUP sample
For bold statements use the \b command.
If you wish to emphasize something use the \i command.
For titles use BIG font sizes, 14 points usually works well.
Remember that all of the commands toggle except for the \s command.
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
