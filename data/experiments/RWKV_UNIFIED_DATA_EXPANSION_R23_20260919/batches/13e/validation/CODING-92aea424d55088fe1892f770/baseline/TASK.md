Your task is to simulate a library management system. First, input several book titles and their authors (titles are unique, ending with END), followed by several commands: BORROW indicates borrowing a book, RETURN indicates returning a book, and SHELVE means to sort all returned but unshelved books and insert them into the bookshelf in order, then output the book title and insertion position (either before the first book or after a specific book). Books should be sorted first by author in ascending order, then by title in ascending order. Before processing the first command, you should sort all books according to this method.

## Input and Output Sample

### Input Example #1

```
"The Canterbury Tales" by Chaucer, G.
"Algorithms" by Sedgewick, R.
"The C Programming Language" by Kernighan, B. and Ritchie, D.
END
BORROW "Algorithms"
BORROW "The C Programming Language"
RETURN "Algorithms"
RETURN "The C Programming Language"
SHELVE
END
```

### Output Example #1

```
Put "The C Programming Language" after "The Canterbury Tales"
Put "Algorithms" after "The C Programming Language"
END
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
