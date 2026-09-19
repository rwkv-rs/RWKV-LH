Determined to discover the ancient mystery—the sound that the fox makes—you went into the forest, armed with a very good digital audio recorder. The forest is, however, full of animals’ voices, and on your recording, many different sounds can be heard. But you are well prepared for your task: you know exactly all the sounds which other animals make. Therefore the rest of the recording—all the unidentified noises—must have been made by the fox.

## Input Format

The first line of input contains the number of test cases \( T \). The descriptions of the test cases follow:

The first line of each test case contains the recording—words over lower case English alphabet, separated by spaces. Each contains at most 100 letters and there are no more than 100 words. The next few lines are your pre-gathered information about other animals, in the format `<animal> goes <sound>`. There are no more than 100 animals, their names are not longer than 100 letters each and are actual names of animals in English. There is no `fox goes ...` among these lines.

The last line of the test case is exactly the question you are supposed to answer: `what does the fox say?`

## Output Format

For each test case, output one line containing the sounds made by the fox, in the order from the recording. You may assume that the fox was not silent (contrary to popular belief, foxes do not communicate by Morse code).

## Sample Input and Output

### Input Sample #1

```
1
toot woof wa ow ow ow pa blub blub pa toot pa blub pa pa ow pow toot
dog goes woof
fish goes blub
elephant goes toot
seal goes ow
what does the fox say?
```

### Output Sample #1

```
wa pa pa pa pa pa pow
```

## Notes/Hints

Time limit: 1000 ms, Memory limit: 1048576 kB.

Central Europe Regional Contest (CERC) 2013

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
