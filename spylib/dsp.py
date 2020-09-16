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
  def __init__(self, coefs=[0] * 16, gain=0, pred_scale=0, yn1=0, yn2=0, loop_pred_scale=0, loop_yn1=0, loop_yn2=0):
    self.gain = gain
    self.pred_scale = pred_scale
    self.yn1 = yn1
    self.yn2 = yn2
    self.loop_pred_scale = loop_pred_scale
    self.loop_yn1 = loop_yn1
    self.loop_yn2 = loop_yn2
    self.coef = coefs
    print("Gain: %d PredScale: %d Yn1: %d Yn2: %d LoopPredScale: %d LoopYn1: %d LoopYn2: %d" % (self.gain, self.pred_scale, self.yn1, self.yn2, self.loop_pred_scale, self.loop_yn1, self.loop_yn2))
    print("Coef: %s" % str(self.coef)) 

class Dsp:
  def __init__(self, data, info):
    self.data = data
    self.info = info
  
  def decode(self, samples, output):
    hist1 = self.info.yn1
    hist2 = self.info.yn2
    coefs = self.info.coef
    frameCount = int(DivideByRoundUp(samples, SAMPLES_PER_FRAME))
    samplesRemaining = samples
    
    bytesWritten = 0
    bytesRead = 0
    for i in range(frameCount):
      header = read_u8(self.data, bytesRead)#self.data.read(1)
      bytesRead += 1
      coef_index = (header >> 4) & 0xF
      scale = 1 << (header & 0xF)
      coef1 = coefs[coef_index * 2]
      coef2 = coefs[coef_index * 2 + 1]
      
      samplesToRead = int(MIN(SAMPLES_PER_FRAME, samplesRemaining))
      for s in range(samplesToRead):
        nibble = read_u8(self.data, bytesRead)
        if s % 2 == 0:
          sample = GetHighNibble(nibble)
        else:
          sample = GetLowNibble(nibble)
          bytesRead += 1
        if sample >= 8:
          sample -= 16
        sample = (((scale * sample) << 11) + 1024 + (coef1 * hist1 + coef2 * hist2)) >> 11
        finalSample = Clamp16(sample)
        
        hist2 = hist1
        hist1 = finalSample
        write_s16(output, bytesWritten, finalSample)
        bytesWritten += 2
      
      samplesRemaining -= samplesToRead
  

class DspEntry(Dsp):
  def __init__(self, gsb_entry, coefs, gain=0, pred_scale=0, yn1=0, yn2=0, loop_pred_scale=0, loop_yn1=0, loop_yn2=0):
    self.gsb_entry = gsb_entry
    info = ADPCMINFO(coefs, gain, pred_scale, yn1, yn2, loop_pred_scale, loop_yn1, loop_yn2)
    print(gsb_entry.name)
    super(DspEntry, self).__init__(self.gsb_entry.data, info)
  
  def decode_to_wave(self,output_path):
    wave_data = BytesIO()
    self.decode((self.gsb_entry.data_size / BYTES_PER_FRAME) * SAMPLES_PER_FRAME, wave_data)
    
    sampleRate = 44100.0 # hertz

    wavef = wave.open(output_path,'w')
    wavef.setnchannels(1) # mono
    wavef.setsampwidth(2) 
    wavef.setframerate(sampleRate)
    
    wave_data.seek(0)
    wavef.writeframesraw(wave_data.read())
    #for i in range(int(duration * sampleRate)):
    #value = int(32767.0*math.cos(frequency*math.pi*float(i)/float(sampleRate)))
    #data = struct.pack('<h', value)
    #wavef.writeframesraw( data )

    #wavef.writeframes('')
    wavef.close()