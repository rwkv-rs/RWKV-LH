#!/usr/bin/env python3

import sys

def read_line():
    return sys.stdin.readline()

def parse_track(line):
    sx, sy, m = map(int, line.split())
    segments = []
    for _ in range(m):
        d, c = read_line().split()
        segments.append((int(d), c))
    return sx, sy, segments

def simulate(sx, sy, segments):
    x, y = sx, sy
    for d, c in segments:
        if c == 'X':
            x += d
        else:
            y += d
    return x, y

def main():
    sx, sy, segs_a = parse_track(read_line())
    tx, ty, segs_b = parse_track(read_line())

    path_a = []
    x, y = sx, sy
    for d, c in segs_a:
        if c == 'X':
            x += d
        else:
            y += d
        path_a.append((x, y))

    path_b = []
    x, y = tx, ty
    for d, c in segs_b:
        if c == 'X':
            x += d
        else:
            y += d
        path_b.append((x, y))

    min_dist = float('inf')
    for px, py in path_a:
        for qx, qy in path_b:
            dist = ((px - qx) ** 2 + (py - qy) ** 2) ** 0.5
            if dist < min_dist:
                min_dist = dist

    print("{:.2f}".format(min_dist))

if __name__ == "__main__":
    main()
