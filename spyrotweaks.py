import re
import yaml
import os
from io import BytesIO
from collections import namedtuple
from collections import OrderedDict
import copy
from random import Random

from fs_helpers import *
from spylib import texture_utils
from spylib.rkv import RKV
from paths import ASSETS_PATH, ASM_PATH
import sys
  
PAL_FREE_SPACE_RAM_ADDRESS = 0x805960BC
PAL_DOL_SIZE = 0x3EDB80

PAL_DOL_SECTION_OFFSETS = [
  # Text section
  0x0100, # section .init
  0x2600, # section .text
  PAL_DOL_SIZE, # Custom .text2 section
  
  # Data sections
  0x353680, # section .extab
  0x3536E0, # section .extabindex
  0x353740, # section .ctors
  0x353940, # section .dtors
  0x353960, # section .rodata
  0x36D0E0, # section .data
  0x3E2880, # section .sdata
  0x3E4120, # section .sdata2
]

PAL_DOL_SECTION_ADDRESSES = [
  # Text sections
  0x80003100, # section .init
  0x800056c0, # section .text
  PAL_FREE_SPACE_RAM_ADDRESS, # Custom .text2 section
  
  # Data sections
  0x80005600, # section .extab
  0x80005660, # section .extabindex
  0x80356740, # section .ctors
  0x80356940, # section .dtors
  0x80356960, # section .rodata
  0x803700e0, # section .data
  0x80587980, # section .sdata
  0x8058c620, # section .sdata2
  
  # Bss sections
  #0x803e5880, # section .bss
  #0x80589220, # section .sbss
  #0x80596080, # section .sbss2
]

PAL_DOL_SECTION_SIZES = [
  # Text sections
  0x002500, # section .init
  0x351080, # section .text
  -1, # Custom .text2 section. Placeholder since we don't know the size until the patch has been applied.
  # Data sections
  0x00060, # section .extab
  0x00060, # section .extabindex
  0x00200, # section .ctors
  0x00020, # section .dtors
  0x19780, # section .rodata
  0x757A0, # section .data
  0x018A0, # section .sdata
  0x09A60, # section .sdata2
  
  # Bss sections
  #0x1A2100, # section .bss
  #0x3400, # section .sbss
  #0x3C, # section .sbss2
]

PAL_INSTRUCTION_REPLACEMENTS = [
  0x802A1AF0, # Original
  0x802A1AF8, # 805960BC
  
  0x802A1AE8, # Original
  0x802A1AEC, # 805A60C0
  0x8029A654, # Original
  0x8029A658, # 805A60C0
  0x80003324, # Original
  0x80003328, # 805A60C0
  
  0x8029A61C, # Original
  0x8029A620, # 805A80C0
  0x802E38B8, # Original
  0x802E38BC, # 805A80C0
  0x802E394C, # Original
  0x802E3950, # 805A80C0
]

NTSC_FREE_SPACE_RAM_ADDRESS = 0x805954BC
NTSC_DOL_SIZE = 0x3ED0A0

# These are from main.dol. Hardcoded since it's easier than reading them from the dol.
NTSC_DOL_SECTION_OFFSETS = [
  # Text sections
  0x0100, # section .init
  0x2600, # section .text
  NTSC_DOL_SIZE, # Custom .text2 section
  
  # Data sections
  0x352DA0, # section .extab
  0x352E00, # section .extabindex
  0x352E60, # section .ctors
  0x353060, # section .dtors
  0x353080, # section .rodata
  0x36C660, # section .data
  0x3E1DC0, # section .sdata
  0x3E3660, # section .sdata2
]

NTSC_DOL_SECTION_ADDRESSES = [
  # Text sections
  0x80003100, # section .init
  0x800056C0, # section .text
  NTSC_FREE_SPACE_RAM_ADDRESS, # Custom .text2 section
  # Bss section at 0x803E4DC0
  # Data sections
  0x80005600, # section .extab
  0x80005660, # section .extabindex
  0x80355E60, # section .ctors
  0x80356060, # section .dtors
  0x80356080, # section .rodata
  0x8036F660, # section .data
  0x80586DC0, # section .sdata
  0x8058BA40, # section .sdata2
]

# Disassembly of section .sbss: 80588660
# Disassembly of section .sbss2: 80595480

NTSC_DOL_SECTION_SIZES = [
  # Text sections
  0x002500, # section .init
  0x3507A0, # section .text
  -1, # Custom .text2 section. Placeholder since we don't know the size until the patch has been applied.
  # Bss section size is 0x1A2000
  # Data sections
  0x00060, # section .extab
  0x00060, # section .extabindex
  0x00200, # section .ctors
  0x00020, # section .dtors
  0x195E0, # section .rodata
  0x75760, # section .data
  0x018A0, # section .sdata
  0x09A40, # section .sdata2
]

NTSC_INSTRUCTION_REPLACEMENTS = [
  0x802A12A4, # Original
  0x802A12AC, # 805954BC
  
  0x802A129C, # Original
  0x802A12A0, # 805A54C0
  0x80299E08, # Original
  0x80299E0C, # 805A54C0
  0x80003324, # Original
  0x80003328, # 805A54C0
  
  0x80299DD0, # Original
  0x80299DD4, # 805A74C0
  0x802E30FC, # Original
  0x802E3100, # 805A74C0
  0x802E3068, # Original
  0x802E306C, # 805A74C0
]

MAXIMUM_ADDITIONAL_STARTING_ITEMS = 47

def set_game_version(game_id):
  global DOL_SECTION_ADDRESSES
  global DOL_SECTION_SIZES
  global DOL_SECTION_OFFSETS
  global FREE_SPACE_INSTRUCTIONS
  global ORIGINAL_FREE_SPACE_RAM_ADDRESS 
  global ORIGINAL_DOL_SIZE
  
  if game_id and game_id.startswith("G6S"):
    if game_id.endswith("E7D"):
      print("Setting up ntsc dol for patching")
      DOL_SECTION_ADDRESSES = NTSC_DOL_SECTION_ADDRESSES
      DOL_SECTION_SIZES = NTSC_DOL_SECTION_SIZES
      DOL_SECTION_OFFSETS = NTSC_DOL_SECTION_OFFSETS
      FREE_SPACE_INSTRUCTIONS = NTSC_INSTRUCTION_REPLACEMENTS
      ORIGINAL_FREE_SPACE_RAM_ADDRESS = NTSC_FREE_SPACE_RAM_ADDRESS
      ORIGINAL_DOL_SIZE = NTSC_DOL_SIZE
    elif game_id.endswith("P7D"):
      print("Setting up pal dol for patching")
      DOL_SECTION_ADDRESSES = PAL_DOL_SECTION_ADDRESSES
      DOL_SECTION_SIZES = PAL_DOL_SECTION_SIZES
      DOL_SECTION_OFFSETS = PAL_DOL_SECTION_OFFSETS
      FREE_SPACE_INSTRUCTIONS = PAL_INSTRUCTION_REPLACEMENTS
      ORIGINAL_FREE_SPACE_RAM_ADDRESS = PAL_FREE_SPACE_RAM_ADDRESS
      ORIGINAL_DOL_SIZE = PAL_DOL_SIZE

def address_to_offset(address):
  # Takes an address in one of the sections of main.dol and converts it to an offset within main.dol.
  for section_index in range(len(DOL_SECTION_OFFSETS)):
    section_offset = DOL_SECTION_OFFSETS[section_index]
    section_address = DOL_SECTION_ADDRESSES[section_index]
    section_size = DOL_SECTION_SIZES[section_index]
    
    if section_address <= address < section_address+section_size:
      offset = address - section_address + section_offset
      return offset
  
  raise Exception("Unknown address: %08X" % address)

def offset_to_address(offset):
  # Takes an offset in main.dol and converts it to a RAM address, assuming it is part of main.dol that gets loaded into RAM.
  for section_index in range(len(DOL_SECTION_OFFSETS)):
    section_offset = DOL_SECTION_OFFSETS[section_index]
    section_address = DOL_SECTION_ADDRESSES[section_index]
    section_size = DOL_SECTION_SIZES[section_index]
    
    if section_offset <= offset < section_offset+section_size:
      address = offset - section_offset + section_address
      return address
  
  # Return None when the offset is not inside of any section.
  return None

def split_pointer_into_high_and_low_half_for_hardcoding(pointer):
  high_halfword = (pointer & 0xFFFF0000) >> 16
  low_halfword = pointer & 0xFFFF
  
  if low_halfword >= 0x8000:
    # If the low halfword has the highest bit set, it will be considered a negative number.
    # Therefore we need to add 1 to the high halfword (equivalent to adding 0x10000) to compensate for the low halfword being negated.
    high_halfword = high_halfword+1
  
  return high_halfword, low_halfword

def apply_patch(self, patch_name, sub_asm_path=None):
  asmPath = ASM_PATH
  if sub_asm_path != None:
    asmPath = os.path.join(asmPath, sub_asm_path)
  
  if not os.path.exists(asmPath) and getattr( sys, 'frozen', False ):
    asmPath = os.path.join(os.path.dirname(sys.executable), "asm")
    if sub_asm_path != None:
      asmPath = os.path.join(asmPath, sub_asm_path)
  
  if not os.path.exists(asmPath):
    print("Doesn't exist!")
    return
  global size
  with open(os.path.join(asmPath, patch_name + "_diff.txt")) as f:
    diffs = yaml.safe_load(f)
  
  for file_path, diffs_for_file in diffs.items():
    data = self.get_raw_file(file_path)
    for org_address, new_bytes in diffs_for_file.items():
      if file_path == "sys/main.dol":
        if org_address >= ORIGINAL_FREE_SPACE_RAM_ADDRESS:
          add_custom_functions_to_free_space(self, new_bytes, org_address - ORIGINAL_FREE_SPACE_RAM_ADDRESS)
          continue
        else:
          offset = address_to_offset(org_address)
      else:
        offset = org_address
      
      write_and_pack_bytes(data, offset, new_bytes, "B"*len(new_bytes))

def add_custom_functions_to_free_space(self, new_bytes, offset=0):
  dol_data = self.get_raw_file("sys/main.dol")
  
  # First write our custom code to the end of the dol file.
  patch_length = len(new_bytes) + offset
  print("Applying patch at %08X : %08X" % (ORIGINAL_DOL_SIZE + offset, ORIGINAL_FREE_SPACE_RAM_ADDRESS + offset))
  write_and_pack_bytes(dol_data, ORIGINAL_DOL_SIZE + offset, new_bytes, "B"*len(new_bytes))
  
  # Next add a new text section to the dol (Text2).
  write_u32(dol_data, 0x08, ORIGINAL_DOL_SIZE) # Write file offset of new Text2 section (which will be the original end of the file, where we put the patch)
  write_u32(dol_data, 0x50, ORIGINAL_FREE_SPACE_RAM_ADDRESS) # Write loading address of the new Text2 section
  write_u32(dol_data, 0x98, patch_length) # Write length of the new Text2 section
  
  # Update the constant for how large the .text2 section is so that addresses in this section can be converted properly by address_to_offset.
  DOL_SECTION_SIZES[2] = patch_length
  # Next we need to change a hardcoded pointer to where free space begins. Otherwise the game will overwrite the custom code.
  padded_patch_length = ((patch_length + 3) & ~3) # Pad length of patch to next 4 just in case
  new_start_pointer_for_default_thread = ORIGINAL_FREE_SPACE_RAM_ADDRESS + padded_patch_length # New free space pointer after our custom code
  high_halfword, low_halfword = split_pointer_into_high_and_low_half_for_hardcoding(new_start_pointer_for_default_thread)
  # Now update the asm instructions that load this hardcoded pointer.
  write_u32(dol_data, address_to_offset(FREE_SPACE_INSTRUCTIONS[0]), 0x3C600000 | high_halfword)
  write_u32(dol_data, address_to_offset(FREE_SPACE_INSTRUCTIONS[1]), 0x38030000 | low_halfword)
  # We also update another pointer which seems like it should remain at 0x10004 later in RAM from the pointer we updated.
  # (This pointer was originally 0x805A54C0.)
  # Updating this one may not actually be necessary to update, but this is to be safe.
  new_end_pointer_for_default_thread = new_start_pointer_for_default_thread + 0x10004
  high_halfword, low_halfword = split_pointer_into_high_and_low_half_for_hardcoding(new_end_pointer_for_default_thread)
  write_u32(dol_data, address_to_offset(FREE_SPACE_INSTRUCTIONS[2]), 0x3C600000 | high_halfword)
  write_u32(dol_data, address_to_offset(FREE_SPACE_INSTRUCTIONS[3]), 0x38030000 | low_halfword)
  write_u32(dol_data, address_to_offset(FREE_SPACE_INSTRUCTIONS[4]), 0x3C600000 | high_halfword)
  write_u32(dol_data, address_to_offset(FREE_SPACE_INSTRUCTIONS[5]), 0x38630000 | low_halfword)
  high_halfword = (new_end_pointer_for_default_thread & 0xFFFF0000) >> 16
  low_halfword = new_end_pointer_for_default_thread & 0xFFFF
  write_u32(dol_data, address_to_offset(FREE_SPACE_INSTRUCTIONS[6]), 0x3C200000 | high_halfword)
  write_u32(dol_data, address_to_offset(FREE_SPACE_INSTRUCTIONS[7]), 0x60210000 | low_halfword)
  new_end_pointer_for_default_thread = new_start_pointer_for_default_thread + 0x12004
  high_halfword, low_halfword = split_pointer_into_high_and_low_half_for_hardcoding(new_end_pointer_for_default_thread)
  write_u32(dol_data, address_to_offset(FREE_SPACE_INSTRUCTIONS[8]), 0x3C600000 | high_halfword)
  write_u32(dol_data, address_to_offset(FREE_SPACE_INSTRUCTIONS[9]), 0x38630000 | low_halfword)
  high_halfword = (new_end_pointer_for_default_thread & 0xFFFF0000) >> 16
  low_halfword = new_end_pointer_for_default_thread & 0xFFFF
  write_u32(dol_data, address_to_offset(FREE_SPACE_INSTRUCTIONS[10]), 0x3C200000 | high_halfword)
  write_u32(dol_data, address_to_offset(FREE_SPACE_INSTRUCTIONS[11]), 0x60210000 | low_halfword)
  write_u32(dol_data, address_to_offset(FREE_SPACE_INSTRUCTIONS[12]), 0x3C200000 | high_halfword)
  write_u32(dol_data, address_to_offset(FREE_SPACE_INSTRUCTIONS[13]), 0x60210000 | low_halfword)