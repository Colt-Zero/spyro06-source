import os
import math
from io import BytesIO
from fs_helpers import *

def swap16(i):
  return struct.unpack("<h", struct.pack(">h", i))[0]

def NibbleCountToSampleCount(nibbleCount):
  frames = int(nibbleCount / 16)
  extraNibbles = int(nibbleCount % 16)
  extraSamples = 0
  if extraNibbles >= 2:
    extraSamples = extraNibbles - 2
  return 14 * frames + extraSamples

def ByteCountToSampleCount(byteCount):
  return NibbleCountToSampleCount(byteCount * 2)

def SampleCountToNibbleCount(sampleCount):
  frames = int(sampleCount / 14)
  extraSamples = int(sampleCount % 14)
  extraNibbles = 0
  if extraSamples != 0:
    extraNibbles = extraSamples + 2
  return 16 * frames + extraNibbles
  
def SampleCountToNibbleCountRoundedUp(sampleCount):
  frames = int(sampleCount / 14)
  extraSamples = int(sampleCount % 14)
  extraNibbles = 0
  if extraSamples != 0:
    extraNibbles = 16
  return 16 * frames + extraNibbles
  
def SampleCountToByteCountRoundedUp(sampleCount):
  return math.ceil(SampleCountToNibbleCountRoundedUp(sampleCount) / 2)

def SampleCountToByteCount(sampleCount):
  return math.ceil(SampleCountToNibbleCount(sampleCount) / 2)

class DSPADPCMINFO:
  def __init__(self, coefs=[0] * 16, interleave = 0x0, byte_count = 0, sample_rate=0, sample_count=0):
    self.byte_count = byte_count
    self.sample_count = sample_count
    self.sample_rate = sample_rate
    self.coef = coefs
    self.interleave = interleave
    print("Bytes: %d Samples: %d Sample rate: %d Interleave: %d" % (self.byte_count, self.sample_count, self.sample_rate, self.interleave))
    print("Coef: %s" % str(self.coef)) 
  

class Dsp:
  def __init__(self, data, info):
    self.data = data
    self.info = info
  
  def read_dsp(self, file_data):
    sample_count = read_u32(file_data, 0x0)
    byte_count = SampleCountToByteCountRoundedUp(sample_count)#int(read_u32(file_data, 0x4) / 2)##data_len(file_data) - 0x60 # 0x60 is the header length
    sample_rate = read_u32(file_data, 0x8)
    coefs = []
    for i in range(16):
      coefs.append(swap16(read_s16(file_data, 0x1C + (i * 2))))
    file_data.seek(0x60)
    self.info = DSPADPCMINFO(coefs, 0x300, byte_count, sample_rate, sample_count)
    self.audio_data = BytesIO(file_data.read())
    if byte_count > data_len(self.audio_data):
      self.audio_data.seek(data_len(self.audio_data))
      self.audio_data.write(b'\0'*(byte_count - data_len(self.audio_data)))
    self.audio_data.seek(0)
  
  def write_dsp(self, output):
    if self.info.sample_count == 0:
      return
    write_u32(output, 0x0, self.info.sample_count)
    write_u32(output, 0x4, SampleCountToNibbleCount(self.info.sample_count))#self.info.byte_count)
    write_u32(output, 0x8, self.info.sample_rate)
    write_u32(output, 0xC, 0)
    write_u32(output, 0x10, 2)
    write_u32(output, 0x14, SampleCountToNibbleCount(self.info.sample_count) - 1)#self.info.byte_count - 1)
    write_u32(output, 0x18, 2)
    for i in range(len(self.info.coef)):
      write_s16(output, 0x1C + i * 2, swap16(self.info.coef[i]))
    write_u32(output, 0x3C, 0x43)
    write_bytes(output, 0x40, bytes(bytearray(0x20)))
    self.data.seek(0);
    write_bytes(output, 0x60, self.data.read())
  
  def save_header_changes(self):
    self.gsb_entry.data_size = self.info.byte_count
    self.gsb_entry.new_data = 1
    self.gsb_entry.sample_count = self.info.sample_count
    self.gsb_entry.sample_rate = self.info.sample_rate
    self.gsb_entry.coefs = self.info.coef
    #write_u32(self.data, self.gsb_entry.entry_offset + 0x24, self.info.sample_count)
    #write_u32(self.data, self.gsb_entry.entry_offset + 0x28, self.info.byte_count)
    #write_u16(self.data, self.gsb_entry.entry_offset + 0x2C, self.info.sample_rate)
    #for i in range(len(self.info.coef)):
    #  write_s16(self.data, self.gsb_entry.entry_offset + 0x32 + i * 2, swap16(self.info.coef[i]))

class DspEntry(Dsp):
  def __init__(self, gsb_entry, coefs, interleave, byte_count, sample_rate, sample_count=0):
    self.gsb_entry = gsb_entry
    if sample_count == 0:
      sample_count = ByteCountToSampleCount(byte_count) #sample_count = int(byte_count * 1.75)
    info = DSPADPCMINFO(coefs, interleave, byte_count, sample_rate, sample_count)
    print(gsb_entry.name)
    super(DspEntry, self).__init__(self.gsb_entry.data, info)
  
  def import_dsp(self, file_data):
    self.read_dsp(file_data)
  
  def export_dsp(self, output_path):
    dsp_data = BytesIO()
    self.write_dsp(dsp_data)
    if data_len(dsp_data) == 0:
      return
    dsp_data.seek(0)
    with open(output_path, "wb") as f:
      f.write(dsp_data.read())
   
  def save_changes(self):
    print("Saving dsp changes for %s..." % self.gsb_entry.name)
    self.gsb_entry.data = BytesIO(self.audio_data.read())
    #write_bytes(self.gsb_entry.data, self.gsb_entry.data_offset, )
    self.save_header_changes()
