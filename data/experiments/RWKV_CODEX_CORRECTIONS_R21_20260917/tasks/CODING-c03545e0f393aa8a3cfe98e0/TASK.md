{
  "examples": [
    {
      "input": "-2 1",
      "output": "white"
    },
    {
      "input": "2 1",
      "output": "black"
    },
    {
      "input": "4 3",
      "output": "black"
    }
  ],
  "input": "Two integers x and y (-1000 <= x, y <= 1000).",
  "logic": "The color is white if (x^2 + y^2) % 2 == 0, otherwise black.",
  "output": "Print 'white' if the area is white, 'black' otherwise.",
  "task": "Find the color of the area damaged by the ball at the given coordinates."
}
