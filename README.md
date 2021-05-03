# Quantum Minesweeper Solver

## How to use

There are two ways to use this program: specifying the Minesweeper grid through
the command line, or reading a Minesweeper grid from a file.

### Specifying a Minesweeper grid through the command line

First, run the script directly.

```
$ ./execute_local.py
? for each unknown tile
1-8 for each hint
0 for empty spaces
All lines must be the same length
Input a Minesweeper grid:
```

Then you can input a Minesweeper grid, with each row of the puzzle on its
own line.
For example, you could type:

```
???
221
```

When you are finished, press enter twice to submit.

### Specifying a Minesweeper grid from a file

You can also input a grid from a file. For example:

```
$ ./execute_local.py examples/zero.txt
```

This will solve the file `examples.zero.txt`.
These files have the exact same format as you would type for the command line.

## Arguments

### Number of shots

The number of shots is the number of times the program will execute the generated
circuit, with higher numbers of shots resulting in more accurate results. This number
is `1000` by default, but can be changed with the `-s` option.

### Number of iterations

The number of iterations is the number of Grover iterations that will occur for each
individual circuit execution. The number of iterations is important, because too few
or too many iterations will produce noisier results, regardless of the number of shots.
By default, the number of iterations is estimated to be `sqrt(2**n) * π/4`, where `n`
is the number of known cells. This is correct if there is only one correct answer.

The number of iterations can be directly overriden with the `-i` option.

If the number of answers that ta puzzle will have is known beforehand, then the
number of iterations can be better estimated with the `-a` flag.
This will compute the number of iterations
as `sqrt(2**n/a) * π/4`, where `n` is the number of unknown cells, and `a` is the
number of answers.