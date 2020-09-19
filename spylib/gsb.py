import os
from io import BytesIO
from fs_helpers import *

import unicodedata
import re
import string

from spylib.vgadsp import DspEntry

def ascii_string(string):
  try:
    string.encode('ascii')
  except UnicodeEncodeError:
    return ascii_string(string[:-1])#pass  # string is not ascii
  else:
    pass  # string is ascii
  return string

def slugify(value, allow_unicode=False):
  """
  Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
  dashes to single dashes. Remove characters that aren't alphanumerics,
  underscores, or hyphens. Convert to lowercase. Also strip leading and
  trailing whitespace, dashes, and underscores.
  """
  value = str(value)
  if allow_unicode:
      value = unicodedata.normalize('NFKC', value)
  else:
      value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
  value = re.sub(r'[^\w\s-]', '', value.lower())
  value = re.sub(r'[-\s]+', '-', value).strip('-_')
  value = re.sub(r'x[0-9a-f]{2}','', value)
  return value[1:]

class GSB:
  def __init__(self, file_entry, data):
    self.file_entry = file_entry
    self.data = data
    data = self.data
    self.archive_size = data_len(data)
    self.data_section_size = read_u32(data, 0x8)
    
    base = 0x20
    self.entries_list_begin = base
    self.entries_list_end = self.archive_size - self.data_section_size
    self.num_entries = int((self.entries_list_end - self.entries_list_begin) / GSBEntry.ENTRY_SIZE)
    
    self.gsb_entries = []
    for gsb_index in range(self.num_entries):
      data.seek(base)
      gsb_entry = GSBEntry(self, base, self.entries_list_end)
      #gsb_entry.read(self.entries_list_end)
      self.gsb_entries.append(gsb_entry)
      base += GSBEntry.ENTRY_SIZE
    
    sorted_entries = self.gsb_entries.copy()
    sorted_entries.sort(key=lambda x: x.data_offset)
    
    for gsb_index in range(self.num_entries):
      gsb_entry = sorted_entries[gsb_index]
      offset = gsb_entry.data_offset
      next_offset = 0
      orig_data_size = gsb_entry.data_size
      if gsb_index < self.num_entries - 1:
        next_entry = sorted_entries[gsb_index + 1]
        next_offset = next_entry.data_offset
      if next_offset > 0:
        if orig_data_size != next_offset - offset:
          gsb_entry.real_data_size = next_offset - offset
      gsb_entry.read(self.entries_list_end)
    
    self.instantiated_object_files = {}
  
  def get_entry(self, name):
    for gsb_entry in self.gsb_entries:
      if gsb_entry.name == name:
        return gsb_entry
    return None
  
  def get_entries(self):
    return gsb_entries
  
  def get_sound(self, entry_name):
    if entry_name in self.instantiated_object_files:
      return self.instantiated_object_files[entry_name]
    
    gsb_entry = self.get_entry(entry_name)
    if gsb_entry is None:
      return None
    
    dsp = DspEntry(gsb_entry)
    self.instantiated_object_files[entry_name] = dsp
    return dsp
  
  def add_entry(self, name, new_data):
    gsb_entry = GSBEntry(self, self.entries_list_end, self.entries_list_end + GSBEntry.ENTRY_SIZE, data=new_data)
    self.entries_list_end += GSBEntry.ENTRY_SIZE
    self.archive_size += data_len(new_data)
    self.gsb_entries.append(gsb_entry)
    return gsb_entry
  
  def add_sound(self):
    return None
  
  def delete_entry(self, gsb_entry):
    self.gsb_entries.remove(gsb_entry)
  
  def save_changes(self):
    self.data.seek(0x20)
    self.data.truncate(0x20)
    
    self.entries_list_begin = self.data.tell()
    next_gsb_entry_offset = self.entries_list_begin
    print ("Begining of gsb entries: %s" % hex(self.entries_list_begin))
    #entry_count = 0
    for gsb_entry in self.gsb_entries:
      gsb_entry.entry_offset = next_gsb_entry_offset
      self.data.seek(gsb_entry.entry_offset)
      self.data.write(b'\0'*(GSBEntry.ENTRY_SIZE ))
      next_gsb_entry_offset += GSBEntry.ENTRY_SIZE
      #entry_count += 1
      #print ("entry #%d" % entry_count)
    
    self.gsb_data_list_offset = self.data.tell() #  entries_list_end
    self.entries_list_end = self.gsb_data_list_offset
    print ("Begining of data entries: %s" % hex(self.entries_list_end))
    print ("%d entries in data" % len(self.gsb_entries))
    next_gsb_data_offset = 0
    for gsb_entry in self.gsb_entries:
      # TODO: Figure out how to make changing offset work
      #    because having the ability to have larger audio
      #      files would be nice
      #if next_gsb_data_offset > gsb_entry.data_offset:
      #  gsb_entry.data_offset = next_gsb_data_offset
      gsb_entry.data_offset = next_gsb_data_offset
      if gsb_entry.new_data == 1:
        self.data.seek(self.gsb_data_list_offset + gsb_entry.data_offset)
        #self.data.write(b'\0'*gsb_entry.real_data_size)
        gsb_entry.real_data_size = data_len(gsb_entry.data)
        #gsb_entry.data_offset = self.archive_size - self.gsb_data_list_offset
        #self.archive_size += gsb_entry.real_data_size
      gsb_entry.save_changes()
      
      self.data.seek(self.gsb_data_list_offset + gsb_entry.data_offset)
      print("Saving entry %s data at %s"% (gsb_entry.name, hex(self.data.tell())))
      gsb_entry.data.seek(0)
      self.data.write(gsb_entry.data.read(gsb_entry.real_data_size))
      
      next_gsb_data_offset = self.data.tell() - self.gsb_data_list_offset
    
    self.total_num_file_entries = len(self.gsb_entries)
    write_u32(self.data, 0x04, self.total_num_file_entries)
    if data_len(self.data) < self.archive_size:
      self.data.write(b'\0'*(self.archive_size-data_len(self.data)))
    self.data_section_size = self.archive_size - self.entries_list_end
    write_u32(self.data, 0x08, self.data_section_size)
    self.file_entry.data_size = self.archive_size
  
  def extract_all_sounds_to_disk(self, output_directory):
    if not os.path.isdir(output_directory):
      os.mkdir(output_directory)
    
    files_wrote = {}
    
    for gsb_entry in self.gsb_entries:
      if data_len(gsb_entry.data) > 0:
        name = gsb_entry.name
        if gsb_entry.name in files_wrote.values():
          while name in files_wrote.values():
            stripped_name = name.rstrip(string.digits)
            if stripped_name[-1] == '_' and name.rsplit('_', 1)[1].isnumeric():
              number = name.rsplit('_', 1)[1]
              name = stripped_name + ("%d" % (int(number) + 1))
            else:
              name = name + "_1"
          print(os.path.join(output_directory, name))
        files_wrote[name] = name
        #print(name)
        gsb_entry.data.seek(0)
        output_file_path = os.path.join(output_directory, name)
        with open(output_file_path, "wb") as f:
          f.write(gsb_entry.data.read())
  
  def extract_all_sounds_to_disk_dsp(self, output_directory):
    if not os.path.isdir(output_directory):
      os.mkdir(output_directory)
    
    files_wrote = {}
    
    for gsb_entry in self.gsb_entries:
      if data_len(gsb_entry.data) > 0:
        name = gsb_entry.name
        if gsb_entry.name in files_wrote.values():
          while name in files_wrote.values():
            stripped_name = name.rstrip(string.digits)
            if stripped_name[-1] == '_' and name.rsplit('_', 1)[1].isnumeric():
              number = name.rsplit('_', 1)[1]
              name = stripped_name + ("%d" % (int(number) + 1))
            else:
              name = name + "_1"
          print(os.path.join(output_directory, name))
        files_wrote[name] = name + ".dsp"
        output_file_path = os.path.join(output_directory, name + ".dsp")
        
        dsp = DspEntry(gsb_entry, gsb_entry.coefs, gsb_entry.interleave, gsb_entry.data_size, gsb_entry.sample_rate, gsb_entry.sample_count)
        self.instantiated_object_files[name] = dsp
        dsp.export_dsp(output_file_path)
  
  def import_all_sounds_from_disk_dsp(self, import_directory):
    if not os.path.isdir(import_directory):
      return 0
    print(import_directory)
    
    files_wrote = {}
    num_files_overwritten = 0
    
    for gsb_entry in self.gsb_entries:
      if data_len(gsb_entry.data) > 0:
        name = gsb_entry.name
        if gsb_entry.name in files_wrote.values():
          while name in files_wrote.values():
            stripped_name = name.rstrip(string.digits)
            if stripped_name[-1] == '_' and name.rsplit('_', 1)[1].isnumeric():
              number = name.rsplit('_', 1)[1]
              name = stripped_name + ("%d" % (int(number) + 1))
            else:
              name = name + "_1"
          #files_wrote[name] = name + ".dsp"
        file_path = os.path.join(import_directory, name + ".dsp")
        if os.path.isfile(file_path):
          print(file_path)
          with open(file_path, "rb") as f:
            dsp = DspEntry(gsb_entry, gsb_entry.coefs, gsb_entry.interleave, gsb_entry.data_size, gsb_entry.sample_rate, gsb_entry.sample_count)
            data = BytesIO(f.read())
            dsp.import_dsp(data)
            dsp.save_changes()
          num_files_overwritten += 1
        
    
    return num_files_overwritten

def swap16(i):
  return struct.unpack("<h", struct.pack(">h", i))[0]

class GSBEntry:
  ENTRY_SIZE = 0x60
  
  def __init__(self, gsb, entry_offset, data=None):
    self.gsb = gsb
    self.entry_offset = entry_offset
    gsb.data.seek(entry_offset)
    self.real_name = BytesIO(gsb.data.read(0x20))
    self.name = slugify(self.real_name.read(0x20))
    self.data_offset = read_u32(gsb.data, entry_offset + 0x20)
    self.data_size = read_u32(gsb.data, entry_offset + 0x28)
    self.sample_count = read_u32(gsb.data, entry_offset+0x24)
    self.sample_rate = read_u16(gsb.data, entry_offset+0x2C)
    self.UNK_16 = read_u16(gsb.data, entry_offset + 0x2E)
    self.interleave = read_u16(gsb.data, entry_offset+0x30)
    gsb.data.seek(entry_offset + 0x52)
    self.UNK_BYTES = gsb.data.read(0xE)
    self.coefs = self.get_cofficients()
    self.data = data
    self.new_data = 0
    self.real_data_size = self.data_size
  
  def get_cofficients(self):
    coefs = []
    for i in range(16):
      coefs.append(swap16(read_s16(self.gsb.data, self.entry_offset+0x32 + (i * 2))))
    return coefs
  
  def read(self, entries_list_end):
    #self.gsb.data.seek(self.entry_offset+0x32)
    #self.data = BytesIO(self.gsb.data.read(0x20))
    self.gsb.data.seek(self.data_offset + entries_list_end)
    #self.data.write(self.gsb.data.read(self.data_size))
    self.data = BytesIO(self.gsb.data.read(self.real_data_size))
  
  def save_changes(self):
    print("Saving entry %s at offset %s" % (self.name, hex(self.entry_offset)))
    self.gsb.data.seek(self.entry_offset)
    self.real_name.seek(0)
    self.gsb.data.write(self.real_name.read(0x20))
    write_u32(self.gsb.data, self.entry_offset+0x20, self.data_offset)
    write_u32(self.gsb.data, self.entry_offset+0x24, self.sample_count)
    write_u32(self.gsb.data, self.entry_offset+0x28, self.data_size)
    write_u16(self.gsb.data, self.entry_offset+0x2C, self.sample_rate)
    write_u16(self.gsb.data, self.entry_offset+0x2E, self.UNK_16)
    write_u16(self.gsb.data, self.entry_offset+0x30, self.interleave)
    for i in range(len(self.coefs)):
      write_s16(self.gsb.data, self.entry_offset+0x32 + i * 2, swap16(self.coefs[i]))
    self.gsb.data.seek(self.entry_offset+0x52)
    self.gsb.data.write(self.UNK_BYTES)