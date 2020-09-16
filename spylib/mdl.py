import os
from io import BytesIO, StringIO
from fs_helpers import *
import math

# Mdl format notes:
#0x30 byte Header:
# 16b array size at 0x4, correlates to 0x40 byte entries starting at 0x30 and some names at the end of the file
# 16b array size at 0x6, correlates to 0x20 byte entries and some names at the end of the file
# 16b array size at 0x8, correlates to 0x10 byte skeleton entries
# 16b array size at 0xA, correlates to 0x40 byte matrix entries
# 16b array size at 0xC, correlates to 0x40 byte entries... maybe... honestly not sure yet
# 16b submesh count at 0xE, correlates to submesh array in mdg
# 32b unknown value at 0x10, *seems* to always be 0, but I'm not sure yet
# 32b vertex count at 0x14, I think...
# 32b triangle count at 0x18
# 32b unknown value at 0x1C, not sure yet what it's supposed to be
# 0x20 to 0x30 still completely unknown

#Array entries from 0x4:
# 32b array of 8 floats till entryStart+0x20
# 32b array of 8 uints till entryStart+0x40

#Array entries from 0x6:
# 32b array of 4 floats till entryStart+0x10
# 16b array of 8 ushorts(most likely) till entryStart+0x20

#Array entries from 0x8:
# 32b array of 3 floats for x,y,z bone positions till entryStart+0xC
# 32b float for a possible scale value till entryStart+0x10
# Pointer referring the beginning of a skeleton related section
# in the mdg after the end of this section in the mdl?

#Array entries from 0xA:
# 32b 4*4 float matrix till entryStart+0x40

#Array entries from 0xC:
# 

class MdlMdg:
  def __init__(self, data):
    self.data = data
    
class MdlFile:
  def __init__(self, data):
    self.data = data
    self.submesh_count = read_s16(self.data, 0xE)

class MdlFileEntry(MdlFile):
  def __init__(self, mdl_entry):
    self.file_entry = mdl_entry
    super(MdlFileEntry, self).__init__(self.file_entry.data)
  
  def get_submesh_count(self):
    return self.submesh_count

# Mdg format notes:
#Array entries of bones referenced by mdl:
# 32b array of 3 floats for x,y,z bone positions till entryStart+0xC
# 32b uint index into the mdl bone array

#Array of bone connections after mdg bone entries:
# 

class MdgFile():
  def __init__(self, data, submeshCount, output_directory):
    self.data = data
    self.submesh_count = submeshCount
    
    obj_data = StringIO()
    
    faceIndex1 = 0
    faceIndex2 = 0
    data_offset = 0x20
    data_size = data_len(self.data)
    for m in range(self.submesh_count):
      print("Submesh: %d" % m)
      obj_data.write("g submesh %d\n" % m)
      #position, faceCount, condition1, faceBytes, offset2, vertexBytes, uvBytes = self.get_submesh_header(data_offset, data_size)
      
      data_offset = self.get_next_submesh(data_offset, data_size)
      if data_offset >= data_size:
        break
       
      position, faceCount, condition1, faceBytes, offset2, vertexBytes, uvBytes = self.get_submesh_header(data_offset, data_size)
      if position >= data_size:
        break
      
      vertexCount = int(vertexBytes / 12)
      if condition1 == 0:
        vertexCount = int(vertexBytes / 20)
      uvCount = int(uvBytes / 4)
      
      data_offset = position + faceBytes + offset2
      for j in range(vertexCount):
        v1 = read_float(self.data, data_offset)
        v2 = read_float(self.data, data_offset + 0x4)
        v3 = read_float(self.data, data_offset + 0x8)
        data_offset += 0xC
        if condition1 == 0:
          data_offset += 0x8 # seems to dependent on the model
        #print("vertex: %.2f %.2f %.2f" % (v1, v2, v3))
        obj_data.write("v %.6f %.6f %.6f\n" % (v1, v2, v3))
      
      data_offset = position + faceBytes + offset2 + vertexBytes
      for j in range(uvCount):
        u = read_s16(self.data, data_offset) / 4096
        v = read_s16(self.data, data_offset + 0x2) / 4096
        u = math.fmod(u, 1)
        v = math.fmod(v, 1)
        v = 1 - v
        data_offset += 0x4
        #print("UV: %.2f %.2f" % (u, v))
        obj_data.write("vt %.6f %.6f\n" % (u, v))
      
      data_offset = position
      for j in range(faceCount):
        flag = False
        faceVertexCount = read_s16(self.data, data_offset + 0x1)
        data_offset += 0x3
        fv1 = 0
        fv2 = 0
        fv3 = 0
        fv4 = 0
        for k in range(faceVertexCount):
          flag = not flag
          fv5 = fv1
          fv1 = fv3
          fv6 = fv2
          fv2 = fv4
          fv3 = read_s16(self.data, data_offset)
          fv4 = read_s16(self.data, data_offset + 0x7)
          data_offset += 0x9
          if k > 1 and fv5 != fv1 and fv1 != fv3 and fv3 != fv5:
            f1 = faceIndex1 + 1 + fv3
            f2 = faceIndex2 + 1 + fv4
            f3 = faceIndex1 + 1 + fv1
            f4 = faceIndex2 + 1 + fv2
            f5 = faceIndex1 + 1 + fv5
            f6 = faceIndex2 + 1 + fv6
            if flag:
              f1 = (f1 - fv3) + fv5
              f2 = (f2 - fv4) + fv6
              f5 = (f5 - fv5) + fv3
              f6 = (f6 - fv6) + fv4
            #print("face: %d/%d %d/%d %d/%d" % (f1, f2, f3, f4, f5, f6))
            obj_data.write("f %d/%d %d/%d %d/%d\n" % (f1, f2, f3, f4, f5, f6))
      faceIndex1 += vertexCount
      faceIndex2 += uvCount
      data_offset = position + faceBytes + offset2 + vertexBytes + uvBytes
    
    obj_data.seek(0)
    obj_file = open(os.path.join(output_directory, os.path.splitext(self.file_entry.name)[0] + ".obj"), "w")
    obj_file.write(obj_data.read())
    obj_file.close()
  
  def get_next_submesh(self, data_offset, data_size):
    position = data_offset
    while position < data_size:
      position, faceCount, condition1, faceBytes, offset2, vertexBytes, uvBytes = self.get_submesh_header(position, data_size)
      if position >= data_size:
        return data_size
      
      data_offset = position
      
      faceHeaderByte = 0
      for j in range(faceCount):
        faceHeaderByte = read_u8(self.data, data_offset)
        if faceHeaderByte != 0x98:
          break
        faceVertexCount = read_s16(self.data, data_offset + 0x1)
        data_offset += faceVertexCount * 0x9 + 0x3
      
      if faceHeaderByte == 0x98:
        return position - 0x20
    if position >= data_size:
        return data_size
    return position - 0x20
    
  
  def get_submesh_header(self, data_offset, data_size):
    data_offset += 0x6
    
    if data_offset + 0x1A > data_size:
      return data_size, 0, 0, 0, 0, 0, 0
    faceCount = read_s16(self.data, data_offset)
    condition1 = read_s16(self.data, data_offset + 0x2)
    data_offset += 0xA
    faceBytes = read_u32(self.data, data_offset)
    #if data_offset + 0x10 + faceBytes > data_size:
    #  return data_size, 0, 0, 0, 0, 0, 0
    offset2 = read_u32(self.data, data_offset + 0x4)
    #if data_offset + 0x10 + faceBytes + offset2 > data_size:
    #  return data_size, 0, 0, 0, 0, 0, 0
    vertexBytes = read_u32(self.data, data_offset + 0x8)
    #if data_offset + 0x10 + faceBytes + offset2 + vertexBytes > data_size:
    #  return data_size, 0, 0, 0, 0, 0, 0
    uvBytes = read_u32(self.data, data_offset + 0xC)
    #if data_offset + 0x10 + faceBytes + offset2 + vertexBytes + uvBytes > data_size:
    #  return data_size, 0, 0, 0, 0, 0, 0
    position = data_offset + 0x10
    
    return position, faceCount, condition1, faceBytes, offset2, vertexBytes, uvBytes

class MdgFileEntry(MdgFile):
  def __init__(self, mdg_entry, mdl_entry, output_directory):
    self.file_entry = mdg_entry
    print(self.file_entry.name)
    super(MdgFileEntry, self).__init__(self.file_entry.data, mdl_entry.get_submesh_count(), output_directory)