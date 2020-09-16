import os
import wave
from io import BytesIO
from fs_helpers import *

BYTES_PER_FRAME = 8
SAMPLES_PER_FRAME = 14
NIBBLES_PER_FRAME = 16

nibble_to_s8 = [0,1,2,3,4,5,6,7,-8,-7,-6,-5,-4,-3,-2,-1]

def MIN(a, b):
  if a < b:
    return a
  return b
def MAX(a, b):
  if a > b:
    return a
  return b

def DivideByRoundUp(dividend, divisor):
  return (dividend + divisor - 1) / divisor

#def GetLowNibble(value):
#  return nibble_to_s8[value & 0xF]

#def GetHighNibble(value):
#  return nibble_to_s8[(value >> 4) & 0xF]

def GetHighNibble(value):
  return value >> 4 & 0xF

def GetLowNibble(value):
  return value & 0xF

def Clamp16(value):
  if value > 32767:
    return 32767
  if value < -32768:
    return -32768
  return value

class ADPCMINFO:
  def __init__(self, coefs=[0] * 16, interleave = 0x0, gain=0, pred_scale=0, yn1=0, yn2=0, loop_pred_scale=0, loop_yn1=0, loop_yn2=0):
    self.gain = gain
    self.pred_scale = pred_scale
    self.yn1 = yn1
    self.yn2 = yn2
    self.loop_pred_scale = loop_pred_scale
    self.loop_yn1 = loop_yn1
    self.loop_yn2 = loop_yn2
    self.coef = coefs
    self.interleave = interleave
    print("Gain: %d PredScale: %d Yn1: %d Yn2: %d LoopPredScale: %d LoopYn1: %d LoopYn2: %d" % (self.gain, self.pred_scale, self.yn1, self.yn2, self.loop_pred_scale, self.loop_yn1, self.loop_yn2))
    print("Coef: %s" % str(self.coef)) 

class Dsp:
  def __init__(self, data, info):
    self.data = data
    self.info = info
  
  def decode(self, output, sample_count):
    samples_written = 0
    samples_this_block = sample_count
    
    while samples_written < sample_count:
      samples_to_do = SAMPLES_PER_FRAME
      if samples_to_do > sample_count - samples_written:
        samples_to_do = sample_count - samples_written
      if samples_to_do == 0:
        break
      
      self.decode_frame(output, 1, samples_written, samples_to_do)
      
      samples_written += samples_to_do
  
  def decode_frame(self, output, channelspacing, first_sample, end_sample):
    sample_count = 0
    hist1 = self.info.yn1
    hist2 = self.info.yn2
    interleave = self.info.interleave
    
    frames_in = int(first_sample / SAMPLES_PER_FRAME)
    start_sample = first_sample
    first_sample = int(first_sample % SAMPLES_PER_FRAME)
    
    #frame = []
    #for b in range(0x08):
    #  boit = read_u8(self.data, frames_in*(0x08*channelspacing) + int(b/interleave) * interleave * channelspacing + b%interleave + interleave * (channelspacing - 1))
    #  frame.append(boit)
    
    frame_offset = BYTES_PER_FRAME * frames_in
    self.data.seek(frame_offset)
    frame = self.data.read(BYTES_PER_FRAME)
    scale = 1 << ((frame[0] >> 0) & 0xf)
    coef_index = (frame[0] >> 4) & 0xf
    
    coef1 = self.info.coef[coef_index * 2 + 0]
    coef2 = self.info.coef[coef_index * 2 + 1]
    
    for s in range(first_sample, first_sample + end_sample):
      nibbles = frame[0x01 + int(s/2)]
      if s % 1 != 0:
        sample = GetLowNibble(nibbles)
      else:
        sample = GetHighNibble(nibbles)
      if sample >= 8:
        sample -= 16
      sample = ((sample * scale) << 11)
      sample = (sample + 1024 + coef1*hist1 + coef2*hist2) >> 11
      sample = Clamp16(sample)
      write_s16(output, start_sample * channelspacing * 2 + sample_count * 2 + 1, sample)
      sample_count += channelspacing
      
      hist2 = hist1;
      hist1 = sample;
    
    self.info.yn1 = hist1
    self.info.yn2 = hist2

class DspEntry(Dsp):
  def __init__(self, gsb_entry, coefs, interleave, gain=0, pred_scale=0, yn1=0, yn2=0, loop_pred_scale=0, loop_yn1=0, loop_yn2=0):
    self.gsb_entry = gsb_entry
    info = ADPCMINFO(coefs, interleave, gain, pred_scale, yn1, yn2, loop_pred_scale, loop_yn1, loop_yn2)
    print(gsb_entry.name)
    super(DspEntry, self).__init__(self.gsb_entry.data, info)
  
  def decode_to_wave(self,output_path):
    wave_data = BytesIO()
    self.decode(wave_data, (self.gsb_entry.data_size / BYTES_PER_FRAME) * SAMPLES_PER_FRAME)
    
    sampleRate = 44100.0 # hertz

    wavef = wave.open(output_path,'w')
    wavef.setnchannels(1) # mono
    wavef.setsampwidth(2) 
    wavef.setframerate(sampleRate)
    
    wave_data.seek(0)
    wavef.writeframes(wave_data.read())
    #for i in range(int(duration * sampleRate)):
    #value = int(32767.0*math.cos(frequency*math.pi*float(i)/float(sampleRate)))
    #data = struct.pack('<h', value)
    #wavef.writeframesraw( data )

    #wavef.writeframes('')
    wavef.close()