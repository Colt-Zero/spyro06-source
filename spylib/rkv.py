import os
from io import BytesIO
from fs_helpers import *

from spylib.tex import TexFileEntry
from spylib.mdl import MdlFileEntry, MdgFileEntry
from spylib.gsb import GSB

def swap32(i):
  return struct.unpack("<I", struct.pack(">I", i))[0]

class RKV:
  def __init__(self, data):
    self.data = data
    data = self.data
    
    num_files = swap32(read_u32(data, 0x4))
    self.end_of_string_section = swap32(read_u32(data, 0x8))
    base = swap32(read_u32(data, 0x14))
    self.entries_list_offset = base
    qw = num_files * FileEntry.ENTRY_SIZE
    name_base = base + qw
    self.name_list_offset = name_base
    self.file_entries = []
    for file_index in range(num_files):
      to_name = swap32(read_u32(data, base))
      d = swap32(read_u32(data, base + 0x4))
      size = swap32(read_u32(data, base + 0x8))
      offset = swap32(read_u32(data, base + 0xC))
      d = swap32(read_u32(data, base + 0x10))
      base += FileEntry.ENTRY_SIZE
      
      if base < name_base: 
        name_length = swap32(read_u32(data, base)) - to_name
      else:
        name_length = swap32(read_u32(data, 0x8)) - to_name
      name = read_str(data, name_base + to_name, name_length)
      #print(name)
      file_entry = FileEntry(self, name, name_base + to_name, base - FileEntry.ENTRY_SIZE, offset, size)
      #file_entry.read()
      self.file_entries.append(file_entry)
    
    sorted_entries = self.file_entries.copy()
    sorted_entries.sort(key=lambda x: x.data_offset)
    
    for file_index in range(num_files):
      file_entry = sorted_entries[file_index]
      offset = file_entry.data_offset
      next_offset = 0
      orig_data_size = file_entry.data_size
      if file_index < num_files - 1:
        next_entry = sorted_entries[file_index + 1]
        next_offset = next_entry.data_offset
      if next_offset > 0:
        if orig_data_size != next_offset - offset:
          file_entry.data_size = next_offset - offset
      file_entry.read()
      file_entry.data_size = orig_data_size
    
    self.instantiated_object_files = {}
  
  def get_file_entry(self, file_name):
    for file_entry in self.file_entries:
      if file_entry.name == file_name:
        return file_entry
    return None
  
  def get_gsb_entries(self):
    gsb_entries = []
    for file_entry in self.file_entries:
      if os.path.splitext(file_entry.name)[1] == ".gsb":
        gsb_entries.append(file_entry)
    return gsb_entries
  
  def get_tex_entries(self):
    tex_entries = []
    for file_entry in self.file_entries:
      if os.path.splitext(file_entry.name)[1] == ".tex":
        tex_entries.append(file_entry)
    return tex_entries
  
  def get_model_entries(self):
    mdl_entries = {}
    for file_entry in self.file_entries:
      split = os.path.splitext(file_entry.name)
      if split[1] == ".mdl" or split[1] == ".mdg":
        if not split[0] in mdl_entries:
          mdl_entries[split[0]] = [file_entry]
        else:
          mdl_entries[split[0]].append(file_entry)
    return mdl_entries
  
  def get_file(self, file_name):
    if file_name in self.instantiated_object_files:
      return self.instantiated_object_files[file_name]
    
    file_entry = self.get_file_entry(file_name)
    if file_entry is None:
      return None
    
    if file_name.endswith(".tex"):
      tex = TexFileEntry(file_entry)
      self.instantiated_object_files[file_name] = tex
      return tex
    elif file_name.endswith(".mdl"):
      mdl = MdlFileEntry(file_entry)
      self.instantiated_object_files[file_name] = mdl
      return mdl
    elif file_name.endswith(".mdg"):
      mdg = MdgFileEntry(file_entry)
      self.instantiated_object_files[file_name] = mdg
      return mdg
    elif file_name.endswith(".gsb"):
      gsb = GSB(file_entry, file_entry.data)
      self.instantiated_object_files[file_name] = gsb
      return gsb
    else:
      raise Exception("Unknown file type: %s" % file_name)
  
  def add_new_file(self, file_name, file_data):
    file_entry = FileEntry(self, file_name, file_data, data_len(file_data))
    self.file_entries.append(file_entry)
    return file_entry
  
  def add_new_tex_file(self, file, basis_entry_name):
    if basis_entry_name in self.instantiated_object_files:
      return None
    
    print ("Adding new texture file with basis entry: %s" % basis_entry_name)
    basis_entry = self.get_file_entry(basis_entry_name)
    if basis_entry is None:
      return None
    
    file_name_and_path = os.path.split(file) 
    file_path = file_name_and_path[0]
    file_name = file_name_and_path[1]
    
    file_name = os.path.splitext(file_name)[0] + '2.tex'
    basis_data = BytesIO(basis_entry.data.read(basis_entry.data_size))
    file_entry = FileEntry(self, file_name, self.name_list_offset + self.end_of_string_section, self.name_list_offset, data_len(self.data), data_len(basis_data))
    file_entry.data = basis_data
    self.file_entries.append(file_entry)
    
    tex = TexFileEntry(file_entry)
    tex.replace_image_from_path(file)
    tex.save_changes()
    self.instantiated_object_files[basis_entry_name] = tex
    
    return file_name
  
  def delete_file(self, file_entry):
    self.file_entries.remove(file_entry)
  
  def save_changes(self):
    # Repacks the rkv file.
    # Supports changing file's size, name, files being added or removed, etc.
    
    # Cut off all the data after the header since we're replacing it entirely.
    self.data.truncate(0x80)
    self.data.seek(0x80)
    
    #self.file_entries.sort(key=lambda x: x.data_offset)
    
    # Assign the entry offsets for each file entry, but don't actually save them yet because we need to write their data and names first.
    self.entries_list_offset = self.data.tell()
    next_file_entry_offset = self.entries_list_offset
    print ("Begining of file entries: %s" % hex(self.entries_list_offset))
    for file_entry in self.file_entries:
      file_entry.entry_offset = next_file_entry_offset
      self.data.seek(file_entry.entry_offset)
      self.data.write(b'\0'*FileEntry.ENTRY_SIZE)
      next_file_entry_offset += FileEntry.ENTRY_SIZE
    
    # Write the strings for the file entry names.
    self.name_list_offset = self.data.tell()
    print ("Begining of file name entries: %s" % hex(self.name_list_offset))
    next_name_offset = 1
    self.data.write(b'\0'*next_name_offset)
    offsets_for_already_written_names = {}
    for file_entry in self.file_entries:
      name = file_entry.name
      if name in offsets_for_already_written_names:
        offset = offsets_for_already_written_names[name]
      else:
        offset = next_name_offset
        write_str_with_null_byte(self.data, self.name_list_offset+offset, name)
        next_name_offset += len(name) + 1
        offsets_for_already_written_names[name] = offset
      file_entry.name_offset = offset
    
    #self.data.write(b'\0'*0x1F)
    align_data_to_nearest(self.data, 0x20)
    # Write the file data, and save the file entries as well.
    self.file_data_list_offset = self.data.tell() # 8A1E0
    print ("Begining of data entries: %s" % hex(self.file_data_list_offset))
    print ("%d entries in data" % len(self.file_entries))
    next_file_data_offset = 0
    #prev_orig_data_offset = 0
    #prev_orig_data_size = 0
    #shaved_bytes = 0
    for file_entry in self.file_entries:
      #if file_entry.data_offset - prev_orig_data_offset != prev_orig_data_size and prev_orig_data_offset != 0:
      #  shaved_bytes += prev_orig_data_size - (file_entry.data_offset - prev_orig_data_offset)
      #prev_orig_data_offset = file_entry.data_offset
      #prev_orig_data_size = file_entry.data_size
      
      file_entry.data_offset = self.file_data_list_offset + next_file_data_offset
      #file_entry.data_size = data_len(file_entry.data)
      file_entry.save_changes()
      
      self.data.seek(file_entry.data_offset)
      file_entry.data.seek(0)
      self.data.write(file_entry.data.read())
      
      # Pad start of the next file to the next 0x20 bytes.
      #align_data_to_nearest(self.data, 0x20)
      next_file_data_offset = self.data.tell() - self.file_data_list_offset
    
    #print("%d Megabytes shaved" % ((shaved_bytes / 1024) / 1024))
    
    # Update the header.
    write_magic_str(self.data, 0x00, "RKV2", 4)
    self.total_num_file_entries = len(self.file_entries)
    write_u32(self.data, 0x04, swap32(self.total_num_file_entries))
    write_u32(self.data, 0x08, swap32(next_name_offset))
    #write_u32(self.data, 0x0C, 0)
    #write_u32(self.data, 0x10, 0x10)
    write_u32(self.data, 0x14, swap32(self.entries_list_offset))
    write_u32(self.data, 0x18, swap32(self.file_data_list_offset - self.entries_list_offset))
    self.data.seek(0x1C)
    self.data.write(b'\0'*0x64)
    
  
  def extract_all_files_to_disk_flat(self, output_directory):
    # Does not preserve directory structure.
    if not os.path.isdir(output_directory):
      os.mkdir(output_directory)
    
    for file_entry in self.file_entries:
      output_file_path = os.path.join(output_directory, file_entry.name)
      
      file_entry.data.seek(0)
      with open(output_file_path, "wb") as f:
        f.write(file_entry.data.read())
  
  def extract_all_models_to_disk(self, output_directory):
    if not os.path.isdir(output_directory):
      os.mkdir(output_directory)
    
    mdl_entries = self.get_model_entries()
    for model_entries in mdl_entries.values():
      model_entries.sort(key=lambda x: os.path.splitext(x.name)[1])#x.name)
      mdl = MdlFileEntry(model_entries[1])
      mdg = MdgFileEntry(model_entries[0], mdl, output_directory)
  
  def extract_all_textures_to_disk(self, output_directory):
    if not os.path.isdir(output_directory):
      os.mkdir(output_directory)
    
    tex_entries = self.get_tex_entries()
    for tex in tex_entries:
      texture = TexFileEntry(tex)
      file_name = os.path.splitext(tex.name)[0]
      texture.write_png(os.path.join(output_directory, file_name))
  
  def import_all_files_from_disk(self, path):
    num_files_overwritten = 0
    for file in self.file_entries:
      file_path = os.path.join(path, file.name)
      if os.path.isfile(file_path):
        print(file.name)
        with open(file_path, "rb") as f:
          data = BytesIO(f.read())
          file.data = data
          file.data_size = data_len(file.data)
          num_files_overwritten += 1
      elif file.name.endswith(".gsb"):
        gsb = self.get_file(file.name)
        if gsb is not None:
          gsb_files_overwritten = gsb.import_all_sounds_from_disk_dsp(os.path.join(path, os.path.splitext(file.name)[0]))
          num_files_overwritten += gsb_files_overwritten
          if gsb_files_overwritten > 0:
            gsb.save_changes()
      elif file.name.endswith(".tex"):
        file_name = os.path.splitext(file.name)[0] + '.png'
        file_path = os.path.join(path, file_name)
        if os.path.isfile(file_path):
          #new_entry_name = self.add_new_tex_file(file_path, file.name)
          #new_entry = self.get_file_entry(new_entry_name)
          #if new_entry is not None:
            #temp = file.name[:]
            #file.name = new_entry_name[:]
            #new_entry.name = temp
            #temp = file.name_offset
            #file.name_offset = new_entry.name_offset
            #new_entry.name_offset = temp
            #print ("Swapped names %s : %s" % (file.name, new_entry.name))
            #print ("OldSize: %d - New Size: %d" % (file.data_size, new_entry.data_size))
          tex = self.get_file(file.name)
          if tex is not None:
            entry = self.get_file_entry(file.name)
            old_size = entry.data_size
            print ("Replacing %s with %s" % (file.name, file_name))
            width = tex.width
            height = tex.height
            mipmap_count = tex.mipmap_count
            tex.replace_image_from_path(file_path)
            tex.save_changes()
            num_files_overwritten += 1
            image_format = str(tex.format).split('.')
            #entry.data_size = data_len(entry.data)
            print ("Old dimensions: %d*%d - New Dimensions: %d*%d" % (width, height, tex.width, tex.height))
            print ("Old mipmap count: %d - New mipmap count: %d" % (mipmap_count, tex.mipmap_count))
            print ("%s: %s Old size: %d - New size: %d\n" % (image_format[0], image_format[1], old_size, data_len(entry.data)))
    return num_files_overwritten

class FileEntry:
  ENTRY_SIZE = 0x14
  
  def __init__(self, rkv, name, data, data_size):
    self.rkv = rkv
    self.name = name
    self.data = data
    self.data_size = data_size
  
  def __init__(self, rkv, name, name_offset, entry_offset, data_offset, data_size):
    self.rkv = rkv
    self.name = name
    self.name_offset = name_offset
    self.entry_offset = entry_offset
    self.data_offset = data_offset
    self.data_size = data_size
  
  def read(self):
    self.rkv.data.seek(self.data_offset)
    self.data = BytesIO(self.rkv.data.read(self.data_size))
    #self.data_size = data_len(self.data)
  
  def save_changes(self):
    #self.data_size = data_len(self.data)
    
    write_u32(self.rkv.data, self.entry_offset, swap32(self.name_offset))
    write_u32(self.rkv.data, self.entry_offset+0x8, swap32(self.data_size))
    write_u32(self.rkv.data, self.entry_offset+0xC, swap32(self.data_offset))