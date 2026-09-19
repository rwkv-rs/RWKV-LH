Graphical User Interface of Elements
The graphical user interface (GUI) elements include buttons, text boxes, scroll bars, drop-down menus, and scrollable list boxes. These controls are known as widgets. The widgets' position, allocated space, and size changes together constitute the geometry of a window.

#### Geometry Management Scheme
A geometry management scheme uses special rectangular frames to contain and combine other widgets. A frame that allocates its space to other frames is called a parent frame, while the frames being allocated space are known as child frames. A frame without a parent frame is called a root frame, and its size is specified by the user (as part of the input data). This problem requires determining the space allocation and the positioning of frames within root frames of various sizes.

The cavities in a frame refer to the space not occupied by child frames. When creating a new child frame, it is allocated a strip that either extends the entire width along the top or bottom edge (referred to as a horizontal child frame) or the entire height along the right or left edge (referred to as a vertical child frame). Thus, when a new child frame is added, the cavity becomes smaller, but remains rectangular. The process of placing child frames inside their parent is known as packing. Child frames are placed in the cavity according to the packing order.

In the diagram below, several child frames of a parent frame are shown. Frame 1 is first placed along the right edge, then frame 2 along the bottom, frame 3 along the left edge, and finally, frame 4 along the right edge. The cavity is shown in white, representing the space available for subsequent child frames.

#### Sizing of Packed Frames
Each frame covers a grid of pixels. If a root frame covers c columns and r rows of pixels, then the top left pixel has coordinates (0,0), and the bottom right pixel has coordinates (c-1, r-1). The location of a frame is specified by the coordinates of its top left and bottom right pixels.

The minimum size of each frame is determined by the input parameter d and the minimum sizes of its child frames. A frame must be large enough to at least accommodate all its child frames. The minimum sizes of frames are shown as follows:

| Packing Side | Frame Type | Minimum Width                          | Minimum Height                           |
|--------------|------------|----------------------------------------|-----------------------------------------|
| Right or left| Vertical   | Maximum of d and the width necessary for the frame’s children | Maximum of 1 and the height necessary for the frame’s children |
| Bottom or top| Horizontal | Maximum of 1 and the width necessary for the frame’s children | Maximum of d and the height necessary for the frame’s children |

When a frame is larger than these minimum sizes, the excess internal space is allocated to its child frames and/or its cavity. Each frame has an expansion flag (input parameter), which, when set, indicates a vertical frame can become wider, or a horizontal frame can become taller. For example, if the expansion flag is set for a vertical frame, the allocated space expands along the top of the cavity to make the frame taller.

#### Distribution of Horizontal and Vertical Space
Horizontal space allocation proceeds as follows: let x be the number of horizontal pixels by which the parent frame exceeds its minimum width. Let n be the number of vertical child frames with an expansion flag set in the parent frame. If n is non-zero, the x pixels are distributed proportionally; otherwise, the width of the cavity is increased.

Similarly, the allocation of vertical space follows the same principles; horizontal child frames use additional vertical pixels, while vertical child frames remain unchanged, and the cavity height increases.

Examples illustrate the effect of enlarging the root frame. Only frames 4, 6, and 7 have the expansion flag set, so the excess horizontal and vertical space is allocated accordingly.

#### Input Format
The input contains a series of root frames, child frames, and different potential root frame sizes. The input format for each root is as follows:

```
M N
```
M is the total number of frames excluding the root frame, and N is the number of different root frame sizes (both positive integers). The following M lines have the format:

```
n p s d e
```
where n is the frame name (positive integer), p is the parent frame name (0 for the root frame), s is the packing side character (L, R, T, or B), d is the minimum size (positive integer), e is the expansion flag (0 or 1).

The following N lines have the format:

```
c r
```
where c is the number of pixel columns, and r is the number of pixel rows for the root frame (both positive integers).

Root frames are not listed. Child frames do not precede their parent frames. Frames are packed in order, and the input ends with M and N both being 0.

#### Output Format
For each root, list its dimensions (rows x columns) and each frame's name with the coordinates of its top left and bottom right corners. If the root frame size is too small, output “is too small.” Different root sizes outputs are separated by dashes.

#### Sample Input
```
7 1
1 0 R 50 0
2 0 R 10 0
3 0 L 40 0
4 0 R 20 1
5 0 T 30 0
6 5 R 20 0
7 5 L 10 1
1000 1000
2 2
1 0 R 100 1
2 0 T 30 1
100 50
200 100
0 0
```

#### Sample Output
```
Root Frame #1
------------------------------
Display: 1000 X 1000
Frame: 1 (950,0) (999,999)
Frame: 2 (0,990) (949,999)
Frame: 3 (0,0) (39,989)
Frame: 4 (70,0) (949,989)
Frame: 5 (40,0) (69,29)
Frame: 6 (50,0) (69,29)
Frame: 7 (40,0) (49,29)
------------------------------

Root Frame #2
------------------------------
Display: 100 X 50 is too small
------------------------------
Display: 200 X 100
Frame: 1 (1,0) (199,99)
Frame: 2 (0,0) (0,99)
------------------------------
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
