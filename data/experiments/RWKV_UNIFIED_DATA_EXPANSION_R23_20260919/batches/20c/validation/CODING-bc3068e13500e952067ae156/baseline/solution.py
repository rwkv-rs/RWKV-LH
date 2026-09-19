import sys

def main():
    data = sys.stdin.read().splitlines()
    if not data:
        return
    N = int(data[0].strip())
    articles = []
    for i in range(1, N + 1):
        parts = data[i].split()
        L = int(parts[0])
        words = parts[1:]
        articles.append(words)
    M = int(data[N + 1].strip())
    queries = [data[N + 2 + j].strip() for j in range(M)]
    article_word_sets = [set(words) for words in articles]
    for word in queries:
        found = [i + 1 for i, s in enumerate(article_word_sets) if word in s]
        print(" ".join(map(str, found)))

if __name__ == "__main__":
    main()
