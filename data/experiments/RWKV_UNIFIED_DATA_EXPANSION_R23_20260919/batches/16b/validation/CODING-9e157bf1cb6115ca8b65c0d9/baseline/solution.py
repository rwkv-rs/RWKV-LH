import sys

def main():
    text = sys.stdin.read()
    if not text:
        print()
        return

    words = text.split()
    n = len(words)
    if n == 0:
        print()
        return

    # Build adjacency list for word co-occurrences
    adj = [[] for _ in range(n)]
    for i in range(n - 1):
        adj[i].append(i + 1)
        adj[i + 1].append(i)

    # Find all occurrences of each word
    word_positions = {}
    for idx, word in enumerate(words):
        if word not in word_positions:
            word_positions[word] = []
        word_positions[word].append(idx)

    # Precompute comma status for each position
    comma_before = [False] * n
    comma_after = [False] * n

    # Helper to check if a position is at the start of a sentence
    def is_sentence_start(pos):
        if pos == 0:
            return True
        prev_word = words[pos - 1]
        return prev_word.endswith('.')

    # Helper to check if a position is at the end of a sentence
    def is_sentence_end(pos):
        if pos == n - 1:
            return True
        next_word = words[pos + 1]
        return next_word.endswith('.')

    # Process each word and its occurrences
    for word, positions in word_positions.items():
        for pos in positions:
            # Check if preceded by a comma
            if pos > 0 and words[pos - 1] == ',':
                comma_before[pos] = True
            # Check if succeeded by a comma
            if pos < n - 1 and words[pos + 1] == ',':
                comma_after[pos] = True

    # Apply rule 1: add commas before occurrences of a word that is preceded by a comma
    for pos in range(n):
        if comma_before[pos]:
            word = words[pos]
            for next_pos in adj[pos]:
                if next_pos < n and words[next_pos] == word and not comma_before[next_pos]:
                    comma_before[next_pos] = True

    # Apply rule 2: add commas after occurrences of a word that is succeeded by a comma
    for pos in range(n):
        if comma_after[pos]:
            word = words[pos]
            for prev_pos in adj[pos]:
                if prev_pos >= 0 and words[prev_pos] == word and not comma_after[prev_pos]:
                    comma_after[prev_pos] = True

    # Apply rule 3: repeat until no new commas are added
    changed = True
    while changed:
        changed = False
        for pos in range(n):
            if comma_before[pos]:
                word = words[pos]
                for next_pos in adj[pos]:
                    if next_pos < n and words[next_pos] == word and not comma_before[next_pos]:
                        comma_before[next_pos] = True
                        changed = True
            if comma_after[pos]:
                word = words[pos]
                for prev_pos in adj[pos]:
                    if prev_pos >= 0 and words[prev_pos] == word and not comma_after[prev_pos]:
                        comma_after[prev_pos] = True
                        changed = True

    # Build the output
    output_parts = []
    for pos in range(n):
        output_parts.append(words[pos])
        if comma_before[pos]:
            output_parts.append(',')
        if comma_after[pos]:
            output_parts.append(',')

    # Ensure the last word is not followed by a comma
    if output_parts and output_parts[-1] == ',':
        output_parts.pop()

    print(''.join(output_parts))

if __name__ == "__main__":
    main()
