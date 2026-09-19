Bessie and her friend Elsie are tired of their nut shell game and want to play another common game called "Guess the Animal."

At the start of the game, Bessie thinks of an animal (most of the time, she thinks of a cow, making the game quite boring, but occasionally Bessie can come up with something else). Then, Elsie tries to guess the animal Bessie has chosen by asking questions. Each question asks if the animal has a specific characteristic, to which Bessie answers "yes" or "no." For example:

Elsie: "Can this animal fly?"  
Bessie: "No."  
Elsie: "Does this animal eat grass?"  
Bessie: "Yes."  
Elsie: "Can this animal produce milk?"  
Bessie: "Yes."  
Elsie: "Does this animal moo?"  
Bessie: "Yes."  
Elsie: "Then I guess this animal is a cow."  
Bessie: "Correct!"  

If we define the "feasible set" as the set of all animals that match the characteristics asked by Elsie so far, Elsie will continue to ask questions until the feasible set contains only one animal, at which point she will guess that animal. For each question, Elsie chooses a characteristic of an animal to ask about (even if the characteristic does not help her narrow down the feasible set). She will not ask about the same characteristic twice.

Given all the animals and their characteristics that Bessie and Elsie know, determine the maximum number of "yes" answers Elsie can get before correctly guessing the animal.

## Input Format

The first line of input contains the number of animals, $N$ ($2 \le N \le 100$). The following $N$ lines each describe an animal. Each line starts with the name of the animal, followed by an integer $K$ ($1 \le K \le 100$), and then $K$ characteristics of the animal. The names of the animals and their characteristics are strings of up to 20 lowercase letters (`a..z`). No two animals have exactly the same characteristics.

## Output Format

Output the maximum number of "yes" answers Elsie can get before the game ends.

## Sample Input and Output

### Sample Input #1

```
4
bird 2 flies eatsworms
cow 4 eatsgrass isawesome makesmilk goesmoo
sheep 1 eatsgrass
goat 2 makesmilk eatsgrass
```

### Sample Output #1

```
3
```

## Notes/Hints

### Sample Explanation #1

In this example, Elsie could have obtained 3 "yes" answers in the conversation (as shown in the example), and it is not possible to have a conversation with more than 3 "yes" answers.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
