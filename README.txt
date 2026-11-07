BARAJADOR DE HYRULE
An Ocarina of Time randomizer for the Nintendo Switch 2 remake (0400486024DEC000, version 1.0.1).

WHAT YOU NEED
- Your own copy of the game as a .nup file (with the 1.0.1 update).
- An emulator that loads mods on top of .nup games (Lichii with change #203 or newer).
- Python 3.14 (free, python.org). On Windows, tick "Add python.exe to PATH" during the install.
  (Older Python 3.10+ also works if you run:  python -m pip install zstandard)

HOW TO USE IT
1. Open "Barajador de Hyrule.html" in your browser, pick your settings and press Generate.
2. Press "Semilla .json" to download the seed (it includes the hints in English and Spanish).
3. Close the emulator.
   Windows: drag the seed .json file and drop it on "Aplicar semilla.bat".
   Linux/Mac: run "Aplicar semilla.sh" and drop the file into the terminal.
   The first time it asks for your .nup file and your emulator's mod folder ("load").
   Tip: you can drag the .nup and the folder into the window instead of typing the paths.
4. Start the game and begin a new file. The spoiler log is saved as spoiler.txt.

To play without the randomizer, delete the "Barajador de Hyrule" folder from the mod folder.

NOTES
- No game files are included. The program reads what it needs from your .nup and builds a small mod.
- Every seed is checked before it is applied, so it can always be finished.
- The logic comes from the OoT Randomizer (MIT license), adapted to the remake.
