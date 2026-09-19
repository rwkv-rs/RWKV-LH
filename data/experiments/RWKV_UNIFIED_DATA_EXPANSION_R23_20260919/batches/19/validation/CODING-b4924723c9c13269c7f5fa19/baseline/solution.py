import sys


def solve():
    lines = sys.stdin.read().splitlines()
    if not lines:
        return

    # Parse dictionary
    dict_lines = []
    for line in lines:
        if line == "#":
            break
        dict_lines.append(line.strip())

    # Build word -> count
    word_counts = {}
    for word in dict_lines:
        word_counts[word] = word_counts.get(word, 0) + 1

    # Parse puzzles
    puzzles = []
    for line in lines[dict_lines.index("#") + 1:]:
        if line == "#":
            break
        puzzles.append(line.strip())

    # For each puzzle, count how many dictionary words can be formed
    for puzzle in puzzles:
        puzzle_counts = {}
        for ch in puzzle:
            puzzle_counts[ch] = puzzle_counts.get(ch, 0) + 1

        count = 0
        for word, word_counts_dict in word_counts.items():
            ok = True
            for ch, need in word_counts_dict.items():
                if puzzle_counts.get(ch, 0) < need:
                    ok = False
                    break
            if ok:
                count += 1

        print(count)


if __name__ == "__main__":
    solve()
