### Quick How to use

You need only drag and drop your vanilla NTSC iso/gcm copy of The Legend of Spyro:
A New Beginning onto the provided Spyro Assembly Patcher executable. After it is
done, the resulting "Spyro Patched.iso" file is fully ready to be played/tested
with the Dolphin Gamecube emulator or on a modded Wii/Gamecube console.

### Detailed How to use

To use the provided assembly/disassembly scripts in their respective sub folders, you will first
need to install the Python 3.6.6. Though later versions of Python 3 should also work.

Download and install Python 3.6.6 from here: https://www.python.org/downloads/release/python-366/  
"Windows x86-64 executable installer" is the one you want. 

Open the Spyro patcher folder in a command prompt and install dependencies by running:  
`py -3.6 -m pip install -r requirements.txt`

Next, you will need to install the PPC branch of DevkitPro.
https://github.com/devkitPro/installer/releases/latest

After having installed and set up DevkitPPC, you must then then adjust the provided "Path/To/" strings
in the assemble.bat and dissassemble.bat files located within their respective subfolders, with whatever
text editor you may choose.

And after all that, you will be able to use assemble.bat to compile your own assembly code into
the _diff.txt files that are used by this patcher to make modifications to the game's code.


But to have an actual basis for doing that, I would reccomend disassembling the game first. You can
do so by going into the disassemble subdirectory that you contains the bat that you should have modifed
before with the correct PPC Path/To string. The simplest option here to actually disassemble the game
would be to move your TLoS: ANB iso into this directory and then drag and drop the iso onto disassemble.bat.

The other 2 options would be to either open the bat file in a text editor again and replace the %1 with the
path to your TLoS: ANB iso, or open up command prompt and make sure that you are navigated to the disassemble
subdirectory, before dragging and dropping the bat file followed by the iso file into your command prompt.

Whichever option you choose, the patcher will autommatically look into the iso's internal files and disassemble
spyro06.elf, a file that contains all of the game's code with debug symbols. You can use the diassembled code as
your tool for finding out more about how the game works and possibly learn more about assembly code as you go,
I know that I did.


For actually making assembly code changes, you need only edit one of the existing asm files in the asm folder
or create new ones of your own. As it currently stands, the patcher contains 2 asm files, 'apply_patches' that
is being used for making edits to the game's existing code. And "custom_symbols" which is used to make additions
to the original code, without overwriting any of the existing functions or data. After you are satisfied and you
want to give it a run. You need only do a simple run of assemble.bat to compile your assembly code then drag and
drop your Vanilla TLoS: ANB iso onto the Spyro Assembly Patcher.

My final notes for now will be that linker.ld is a manually edited file where you will be able to assign custom names
to memory addresses within the vanilla data, making it easier to read/write code that calls upon data/functions already
provided by the vanilla game. But custom_symbols.txt, unlike linker.ld, is an automatically generated file by assemble.bat
and isn't meant to be edited. It can however, be useful to reference if you want to inspect your custom symbols at their
given addresses while the game is running. And finally the memory address 0x805954BC seen in custom_symbols.asm is the
place where the vanilla game's code/data ends and thus where fresh new data for custom symbols can begin.

### About

This is an assembly patcher for The Legend of Spyro: A New Beginning.
It is mostly aimed toward people who are familiar with PPC assembly code
or people that are willing to take the time to learn.

There is no real documentation available for the game at this current time
so the process of making mods for it with this patcher should be expected
to be fairly challenging. However, I would encouraged anyone reading this
to give it a shot, and try to have fun with whatever it is that they are
trying to make.

This patcher currently only supports the North American Gamecube version of
TLoS: ANB. (MD5: 652a91ff450633d2e1fd2eb7bfdd3571) The European and Japanese
versions of TLoS: ANB won't work, neither will the versions for other consoles.

### Credits

This patcher was adapted for the NTSC Gamecube version of The Legend of Spyro: A New Beginning by:
Colt Zero(on Twitch)/Olivine Ellva(on Discord).

The base for this patcher was originally created and programmed by LagoLunatic, originally purposed
as the Randomizer for: The Legend of Zelda: The Wind Waker

### Running the patcher from source

Source still needs to be cleaned up and is not currently available.
