import sys
import os
from os import listdir
from subprocess import call
from io import BytesIO
import shutil
from pathlib import Path
import re
from random import Random
from collections import OrderedDict
import hashlib
import yaml

from fs_helpers import *
from spylib.rkv import RKV
from spylib.gsb import GSB
from spylib.gcm import GCM
import spyrotweaks as tweaks
from paths import ASM_PATH, ROOT_PATH
import asm.assembler as assembly

with open(os.path.join(ROOT_PATH, "version.txt"), "r") as f:
  VERSION = f.read().strip()

VERSION_WITHOUT_COMMIT = VERSION

CLEAN_SPYRO_ISO_MD5 = 0x652a91ff450633d2e1fd2eb7bfdd3571

class InvalidCleanISOError(Exception):
  pass

def load_ppc_path():
  ppc_path = None
  if getattr( sys, 'frozen', False ) :
    base_path = os.path.dirname(sys.executable)
  else:
    base_path = os.path.dirname(os.path.abspath(__file__))
  
  if not os.path.exists(os.path.join(base_path, "settings.txt")):
    print("Settings file not found. Please provide a valid path to DevkitPPC:")
    ppc_path = write_ppc_path()
  
  with open(os.path.join(base_path, "settings.txt"), 'r') as f:
    settings = f.readlines()
  for l in settings:
    if l.startswith("ppc_path"):
      ppc_path = l.split('=')[1].strip()
  if ppc_path == None:
    print("PPC path not found in settings file. Please provide a valid path to DevkitPPC:")
    ppc_path = write_ppc_path()
  return ppc_path

def write_ppc_path():
  ppc_path = str(input()) 
  if ppc_path != None:
    if not os.path.exists(ppc_path):
      print("The path: " + ppc_path + " is invalid. Please provide a valid path to DevkitPPC:")
      write_ppc_path()
    if not os.path.isfile(assembly.get_bin(os.path.join(ppc_path, "bin"), "powerpc-eabi-as")):
      print("The path: " + ppc_path + " is invalid. Please provide a valid path to DevkitPPC:")
      write_ppc_path()
    
    if getattr( sys, 'frozen', False ) :
      base_path = os.path.dirname(sys.executable)
    else:
      base_path = os.path.dirname(os.path.abspath(__file__))
    
    with open(os.path.join(base_path, "settings.txt"), "w") as f:
      f.write("ppc_path = " + ppc_path)
  return ppc_path

def assemble():
  ppc_path = None
  ppc_path = load_ppc_path()
    
  assembler = None
  if ppc_path != None:
    if not os.path.exists(ppc_path):
      print("The path: " + ppc_path + " is invalid. Please provide a valid path to DevkitPPC:")
      ppc_path = write_ppc_path()
    if not os.path.isfile(assembly.get_bin(os.path.join(ppc_path, "bin"), "powerpc-eabi-as")):
      raise Exception(r"Failed to assemble code: Could not find devkitPPC. Check if devkitPPC is installed to: %s" % ppc_path)
    else:
      assembler = assembly.Assembler(ppc_path)
  
  if assembler != None:
    assembler.Assemble("ntsc")
    assembler.Assemble("pal")

class Patcher:
  def __init__(self, clean_iso_path, patched_output_folder, ppc=False):
    self.patched_output_folder = patched_output_folder
    self.rkvs_by_path = {}
    self.raw_files_by_path = {}
    if not os.path.isfile(clean_iso_path):
      raise InvalidCleanISOError("Clean Spyro ISO does not exist: %s" % clean_iso_path)
    
    self.game_id = self.verify_supported_version(clean_iso_path)
    
    self.gcm = GCM(clean_iso_path)
    self.gcm.read_entire_disc()

    self.verify_correct_clean_iso_md5(clean_iso_path)
    
    ppc_path = None
    if ppc == True:
      ppc_path = load_ppc_path()
    
    self.assembler = None
    if ppc_path != None:
      if not os.path.exists(ppc_path):
        print("The path: " + ppc_path + " is invalid. Please provide a valid path to DevkitPPC:")
        ppc_path = write_ppc_path()
      if not os.path.isfile(assembly.get_bin(os.path.join(ppc_path, "bin"), "powerpc-eabi-as")):
        raise Exception(r"Failed to assemble code: Could not find devkitPPC. Check if devkitPPC is installed to: %s" % ppc_path)
      else:
        self.assembler = assembly.Assembler(ppc_path)
  
  def disassemble(self):
    ppc_path = None
    ppc_path = load_ppc_path()   
    if ppc_path != None:
      if not os.path.exists(ppc_path):
        print("The path: " + ppc_path + " is invalid. Please provide a valid path to DevkitPPC to use this disassembler:")
        ppc_path = write_ppc_path()
      if not os.path.isfile(assembly.get_bin(os.path.join(ppc_path, "bin"), "powerpc-eabi-as")):
        raise Exception(r"Failed to assemble code: Could not find devkitPPC. Check if devkitPPC is installed to: %s" % ppc_path)
      ppc_path = assembly.get_bin(os.path.join(ppc_path, "bin"), "powerpc-eabi-objdump")
      if getattr( sys, 'frozen', False ) :
        asm_path = os.path.join(os.path.dirname(sys.executable), "disassemble")
      else :
        asm_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "disassemble")
      self.disassemble_elf(ppc_path, asm_path, self.get_raw_file("files/spyro06.elf").read())
  
  def extract_gameData(self):
    rkv = self.get_rkv("files/data_gc.rkv")
    if getattr( sys, 'frozen', False ) :
      game_path = os.path.join(os.path.dirname(sys.executable), "data_gc")
    else:
      game_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_gc")
    
    if getattr( sys, 'frozen', False ) :
      custom_data_gc = os.path.join(os.path.dirname(sys.executable), "custom_data_gc")
    else:
      custom_data_gc = os.path.join(os.path.dirname(os.path.abspath(__file__)), "custom_data_gc")
    
    if not os.path.isdir(custom_data_gc):
      os.mkdir(custom_data_gc)
    
    rkv.extract_all_files_to_disk_flat(game_path)
  
  def extract_modelData(self):
    rkv = self.get_rkv("files/data_gc.rkv")
    if getattr( sys, 'frozen', False ) :
      model_path = os.path.join(os.path.dirname(sys.executable), "Experimental/models_gc")
    else:
      model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Experimental/models_gc")
    
    if not os.path.isdir(model_path):
      os.mkdir(model_path)
    
    rkv.extract_all_models_to_disk(model_path)
  
  def extract_textures(self):
    rkv = self.get_rkv("files/data_gc.rkv")
    if getattr( sys, 'frozen', False ) :
      texture_path = os.path.join(os.path.dirname(sys.executable), "textures_gc")
    else:
      texture_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "textures_gc")
    
    if not os.path.isdir(texture_path):
      os.mkdir(texture_path)
    
    if getattr( sys, 'frozen', False ) :
      custom_data_gc = os.path.join(os.path.dirname(sys.executable), "custom_data_gc")
    else:
      custom_data_gc = os.path.join(os.path.dirname(os.path.abspath(__file__)), "custom_data_gc")
    
    if not os.path.isdir(custom_data_gc):
      os.mkdir(custom_data_gc)
    
    rkv.extract_all_textures_to_disk(texture_path)
  
  def extract_cutsceneData(self):
    rkv = self.get_rkv("files/media_gc.rkv")
    if getattr( sys, 'frozen', False ) :
      cutscene_path = os.path.join(os.path.dirname(sys.executable), "media_gc")
      custom_cutscene_path = os.path.join(os.path.dirname(sys.executable), "custom_media_gc")
    else:
      cutscene_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media_gc")
      custom_cutscene_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "custom_media_gc")
    
    if not os.path.isdir(custom_cutscene_path):
      os.mkdir(custom_cutscene_path)
    
    rkv.extract_all_files_to_disk_flat(cutscene_path)
  
  def extract_audioData(self):
    rkv = self.get_rkv("files/data_gc.rkv")
    if getattr( sys, 'frozen', False ) :
      audio_path = os.path.join(os.path.dirname(sys.executable), "Experimental/audio_gc")
      dsp_path = os.path.join(os.path.dirname(sys.executable), "Experimental/dsp_gc")
    else:
      audio_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Experimental/audio_gc")
      dsp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Experimental/dsp_gc")
    
    gsb_entries = rkv.get_gsb_entries()
    
    if not os.path.isdir(dsp_path):
      os.mkdir(dsp_path)
    
    #if not os.path.isdir(audio_path):
    #  os.mkdir(audio_path)
    
    #for gsb_entry in gsb_entries:
    #  gsb = GSB(gsb_entry.data)
    #  gsb.extract_all_sounds_to_disk(os.path.join(audio_path, os.path.splitext(gsb_entry.name)[0]))
    
    for gsb_entry in gsb_entries:
    #if not gsb_entry.name.startswith("CS"):
      gsb = GSB(gsb_entry, gsb_entry.data)
      gsb.extract_all_sounds_to_disk_dsp(os.path.join(dsp_path, os.path.splitext(gsb_entry.name)[0]))
  
  def patch(self):
    if self.game_id.endswith("E7D"):
      sub_asm_path = "ntsc"
    elif self.game_id.endswith("P7D"):
      sub_asm_path = "pal"
    
    if self.assembler != None:
      self.assembler.Assemble(sub_asm_path)
    
    if getattr( sys, 'frozen', False ):
      asm_path = os.path.join(os.path.dirname(sys.executable), "asm")
      custom_game_path = os.path.join(os.path.dirname(sys.executable), "custom_data_gc")
      custom_cutscene_path = os.path.join(os.path.dirname(sys.executable), "custom_media_gc")
    else:
      absPath = os.path.dirname(os.path.abspath(__file__))
      if os.path.basename(os.path.normpath(absPath)) == "asm":
        asm_path = absPath
        absPath = os.path.dirname(absPath)
      else:
        asm_path = os.path.join(absPath, "asm")
      custom_game_path = os.path.join(absPath, "custom_data_gc")
      custom_cutscene_path = os.path.join(absPath, "custom_media_gc")
    tweaks.set_game_version(self.game_id)
    asm_path = os.path.join(asm_path, sub_asm_path)
    print(asm_path)
    asm_files = self.get_asm_files(asm_path, ".asm")
    patches = self.get_asm_files(asm_path, ".txt")
    for p in patches:
      checkString = p.split("_diff.txt")[0] + ".asm"
      if checkString in asm_files or p.endswith("_diff.txt"):
        pat = os.path.splitext(os.path.basename(p))[0]
        pat = pat.split("_diff")[0]
        print("Applying %s patch: %s" % (sub_asm_path, pat))
        tweaks.apply_patch(self, pat, sub_asm_path)#"custom_funcs")
        #tweaks.apply_patch(self, pat)#"apply_changes")
    
    if os.path.exists(custom_game_path) and os.path.isdir(custom_game_path):
      if os.listdir(custom_game_path) != 0:
        rkv = self.get_rkv("files/data_gc.rkv")
        rkv.import_all_files_from_disk(custom_game_path)
    
    if os.path.exists(custom_cutscene_path) and os.path.isdir(custom_cutscene_path):
      if os.listdir(custom_cutscene_path) != 0:
        rkv = self.get_rkv("files/media_gc.rkv")
        rkv.import_all_files_from_disk(custom_cutscene_path)
    
    self.save_patched_iso()
  
  def verify_supported_version(self, clean_iso_path):
    game_id = ""
    with open(clean_iso_path, "rb") as f:
      game_id = try_read_str(f, 0, 6)
    if game_id != "G6SE7D" and game_id != "G6SP7D":
      if game_id and game_id.startswith("G6S"):
        raise InvalidCleanISOError("Invalid version of The Legend of Spyro: A New Beginning. Only the USA version is supported by this patcher.")
      else:
        raise InvalidCleanISOError("Invalid game given as the clean ISO. You must specify a Spyro ISO (USA version).")
    return game_id
  
  def verify_correct_clean_iso_md5(self, clean_iso_path):
    md5 = hashlib.md5()
    
    with open(clean_iso_path, "rb") as f:
      while True:
        chunk = f.read(1024*1024)
        if not chunk:
          break
        md5.update(chunk)
    
    #integer_md5 = int(md5.hexdigest(), 16)
    #if integer_md5 != CLEAN_SPYRO_ISO_MD5:
    #  raise InvalidCleanISOError("Invalid clean Spyro ISO. Your ISO may be corrupted.\n\nCorrect ISO MD5 hash: %x\nYour ISO's MD5 hash: %x" % (CLEAN_SPYRO_ISO_MD5, integer_md5))
  
  def convert_string_to_integer_md5(self, string):
    return int(hashlib.md5(string.encode('utf-8')).hexdigest(), 16)
  
  def get_raw_file(self, file_path):
    file_path = file_path.replace("\\", "/")
    
    if file_path in self.raw_files_by_path:
      return self.raw_files_by_path[file_path]
    else:
      data = self.gcm.read_file_data(file_path)
      self.raw_files_by_path[file_path] = data
      return data
  
  def replace_raw_file(self, file_path, new_data):
    if file_path not in self.gcm.files_by_path:
      raise Exception("Cannot replace file that doesn't exist: " + file_path)
    
    self.raw_files_by_path[file_path] = new_data
  
  def add_new_raw_file(self, file_path, new_data):
    if file_path.lower() in self.gcm.files_by_path_lowercase:
      raise Exception("Cannot add a new file that has the same path and name as an existing one: " + file_path)
    
    self.raw_files_by_path[file_path] = new_data
  
  def get_rkv(self, rkv_path):
    rkv_path = rkv_path.replace("\\", "/")
    
    if rkv_path in self.rkvs_by_path:
      return self.rkvs_by_path[rkv_path]
    else:
      data = self.gcm.read_file_data(rkv_path)
      rkv = RKV(data)
      self.rkvs_by_path[rkv_path] = rkv
      return rkv
  
  def replace_rkv(self, rkv_path, new_data):
    if rkv_path not in self.gcm.files_by_path:
      raise Exception("Cannot replace RARC that doesn't exist: " + rkv_path)
    
    rkv = RKV(new_data)
    self.rkvs_by_path[rkv_path] = rkv
  
  def save_patched_iso(self):
    changed_files = {}
    for file_path, data in self.raw_files_by_path.items():
      changed_files[file_path] = data
    
    for rkv_path, rkv in self.rkvs_by_path.items():
      rkv.save_changes()
      changed_files[rkv_path] = rkv.data
    
    output_file_path = os.path.join(self.patched_output_folder, "Spyro Patched.iso")
    self.gcm.export_disc_to_iso_with_changed_files(output_file_path, changed_files)
  
  def disassemble_elf(self, ppc_path, disasm_path, elf_file):
    with open(os.path.join(disasm_path, "spyro06.elf"), "wb") as f:
      result = f.write(elf_file)
    #if result != 0:
      #raise Exception("Disassembler failed to write elf")
    
    command = [
      ppc_path,
      "--disassemble-zeroes",
      "-m", "powerpc",
      "-D",
      "-EB",
      os.path.join(disasm_path, "spyro06.elf")
    ]
    
    print(" ".join(command))
    print()
    with open(os.path.join(disasm_path, "spyro06.asm"), "wb") as f:
      result = call(command, stdout=f)
    if result != 0:
      raise Exception("Disassembler call failed")
  
  def get_asm_files(self, asm_path, extension):
    #asmfiles = [os.path.join(root, name)
    #         for root, dirs, files in os.walk(path)
    #         for name in files
    #         if name.endswith(extension)]
    #return asmfiles
    return [f for f in listdir(asm_path) if f.endswith(extension)]

if __name__ == '__main__':
  if len(sys.argv) == 3 and sys.argv[1] == "-extract":
    pat = Patcher(sys.argv[2], os.path.dirname(os.path.abspath(sys.argv[2])))
    pat.extract_cutsceneData()
    pat.extract_gameData()
  if len(sys.argv) == 3 and sys.argv[1] == "-extracttextures":
    pat = Patcher(sys.argv[2], os.path.dirname(os.path.abspath(sys.argv[2])))
    pat.extract_textures()
  if len(sys.argv) == 3 and sys.argv[1] == "-extractmodels":
    pat = Patcher(sys.argv[2], os.path.dirname(os.path.abspath(sys.argv[2])))
    pat.extract_modelData()
  if len(sys.argv) == 3 and sys.argv[1] == "-extractaudio":
    pat = Patcher(sys.argv[2], os.path.dirname(os.path.abspath(sys.argv[2])))
    pat.extract_audioData()
  if len(sys.argv) == 3 and sys.argv[1] == "-disasm":
    pat = Patcher(sys.argv[2], os.path.dirname(os.path.abspath(sys.argv[2])))
    pat.disassemble()
  if len(sys.argv) == 3 and sys.argv[1] == "-asm":
    pat = Patcher(sys.argv[2], os.path.dirname(os.path.abspath(sys.argv[2])), True)
    pat.patch()
  if len(sys.argv) == 2 and sys.argv[1] == "-asm":
    assemble()
  if len(sys.argv) == 2 and sys.argv[1] != "-asm":
    pat = Patcher(sys.argv[1], os.path.dirname(os.path.abspath(sys.argv[1])))
    pat.patch()
  #else:
  #print(len(sys.argv))