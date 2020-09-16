### Quick How to use

You need only drag and drop your vanilla NTSC/PAL iso/gcm copy of The Legend of Spyro:
A New Beginning onto the provided Spyro06 Patcher executable. After it is done, the
resulting "Spyro Patched.iso" file is fully ready to be played/tested with the Dolphin
Gamecube emulator or on a modded Wii/Gamecube console.

If you want to extract the files from the game you need only drag and drop your original
copy onto them as well. Extract Raw Files will extract all the base files from the game's
2 main archives in their raw state. Extract Textures will extract the game's textures in png format.

When extracting these, custom folders will be created for you to put modified game files into.
Currently only supports files with their original names and formats, with the exception of textures
which support both the original tex format as well as png. This file replacement feature is new
and mostly untested, so it likely will require further improvement.

### Detailed How to use

To use the provided assembly/disassembly scripts in their respective sub folders, you will first will need
to install the PPC branch of DevkitPro. https://github.com/devkitPro/installer/releases/latest

After having installed and set up DevkitPPC, you must then then either manually adjust the provided "Path/To/"
string in the settings.txt file located within this primary folder, with whatever text editor you may choose.
Or simply try to running any of the assembly/disassembly batch files in their respective sub-folders, it will
automatically prompt you to fill out the correct path, which will be saved.

And after that, you will be able to use the assembly batch files to compile your own assembly code into the
_diff.txt files that are used by this patcher to make modifications to the game's code.

But to have an actual basis for doing that, I would reccomend disassembling the game first. You can do so
by going into the disassemble subdirectory that contains another bat file. You need only drag and drop your
copy of the game onto this batch as well. The patcher will autommatically look into the iso's internal files
and disassemble spyro06.elf, a file that contains all of the game's code with debug symbols. Know however that
this process can take a little while, but you should only need to do it once. You can use the diassembled code
as your tool for finding out more about how the game works and possibly learn more about assembly code as you go,
I know that I did.

For actually making assembly code changes, you need only edit one of the existing asm files in the asm folders
or create new ones of your own. As it currently stands, the patcher contains 2 asm files, 'apply_patches' that
is being used for making edits to the game's existing code. And "custom_symbols" which is used to make additions
to the original code, without overwriting any of the existing functions or data. After you are satisfied and you
want to give it a run. You need only do a simple run of assemble.bat to compile your assembly code then drag and
drop your Vanilla TLoS: ANB iso onto the Spyro Patcher or drag and drop onto the Assemble and Patch file, which
will both assemble and apply the new code.

My final notes for now will be that linker.ld is a manually edited file where you will be able to assign custom names
to memory addresses within the vanilla data, making it easier to read/write code that calls upon data/functions already
provided by the vanilla game. But custom_symbols.txt, unlike linker.ld, is an automatically generated file by assemble.bat
and isn't meant to be edited. It can however, be useful to reference if you want to inspect your custom symbols at their
given addresses while the game is running. And finally the memory address at the start of custom_symbols.asm is the
place where the vanilla game's code/data ends and thus where fresh new data for custom symbols can begin.

### About

This is a patcher for The Legend of Spyro: A New Beginning. It was originally
mostly aimed toward people who are familiar with PPC assembly code but now also
supports direct game file replacements, but for people that are willing to take
the time to learn assembly, I'd encourage that as well.

There is no real documentation available for the game at this current time so
the process of making mods for it with this patcher should be expected to be
fairly challenging. However, I would encouraged anyone reading this to give it
a shot, and try to have fun with whatever it is that they are trying to make.

This patcher is currently tested on the North American Gamecube version of
TLoS: ANB. (MD5: 652a91ff450633d2e1fd2eb7bfdd3571) Support for the European
version is freshly added and hasn't been tested at all. The Japanese version
of TLoS: ANB won't work, neither will the versions for other consoles.

### Credits

This patcher was adapted for the NTSC/PAL Gamecube version of The Legend of Spyro: A New Beginning by:
Colt Zero(on Twitch)/Olivine Ellva(on Discord).

The base for this patcher was originally created and programmed by LagoLunatic, originally purposed
as the Randomizer for: The Legend of Zelda: The Wind Waker

### Running the patcher from source

Source still needs to be cleaned up and is not currently available.
