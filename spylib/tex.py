from io import BytesIO
from enum import Enum

from fs_helpers import *
from spylib.texture_utils import *

class TexFormat(Enum):
  RGB5A3 = 0
  CMPR   = 2

TEX_TO_BTI = {
  TexFormat.RGB5A3: ImageFormat.RGB5A3,
  TexFormat.CMPR  : ImageFormat.CMPR,
}

class Tex:
  def __init__(self, data, header_offset=0):
    self.data = data
    self.header_offset = header_offset
    
    self.read_header(data, header_offset=header_offset)
    
    blocks_wide = (self.width + (self.block_width-1)) // self.block_width
    blocks_tall = (self.height + (self.block_height-1)) // self.block_height
    image_data_size = blocks_wide*blocks_tall*self.block_data_size
    remaining_mipmaps = self.mipmap_count-1
    curr_mipmap_size = image_data_size
    while remaining_mipmaps > 0:
      # Each mipmap is a quarter the size of the last (half the width and half the height).
      curr_mipmap_size = curr_mipmap_size//4
      image_data_size += curr_mipmap_size
      remaining_mipmaps -= 1
      # Note: We don't actually read the smaller mipmaps, we only read the normal sized one, and when saving recalculate the others by scaling the normal one down.
      # This is to simplify things, but a full implementation would allow reading and saving each mipmap individually (since the mipmaps can actually have different contents).
    self.image_data = BytesIO(read_bytes(data, header_offset+self.image_data_offset, image_data_size))
  
  
  def read_header(self, data, header_offset=0):
    self.image_format = TexFormat(read_u32(data, header_offset+0))
    
    self.width = read_u32(data, header_offset+4)
    self.height = read_u32(data, header_offset+8)
    self.mipmap_count = read_u8(data, header_offset+0x14)+1
    
    self.image_data_offset = 0x20 #read_u32(data, header_offset+0x1C)
    self.palette_format = PaletteFormat(1)#read_u8(data, header_offset+9))
    self.palette_data = None
    self.num_colors = 0
    
    #self.alpha_setting = read_u8(data, header_offset+1)
    #self.wrap_s = WrapMode(read_u8(data, header_offset+6))
    #self.wrap_t = WrapMode(read_u8(data, header_offset+7))
    #self.palettes_enabled = bool(read_u8(data, header_offset+8))
    
    #self.num_colors = read_u16(data, header_offset+0xA)
    #self.palette_data_offset = read_u32(data, header_offset+0xC)
    #self.min_filter = FilterMode(read_u8(data, header_offset+0x14))
    #self.mag_filter = FilterMode(read_u8(data, header_offset+0x15))
    #self.min_lod = read_u8(data, header_offset+0x16)
    #self.max_lod = read_u8(data, header_offset+0x17) # seems to be equal to (mipmap_count-1)*8
    #self.unknown_3 = read_u8(data, header_offset+0x19)
    #self.lod_bias = read_u16(data, header_offset+0x1A)
  
  def save_header_changes(self):
    write_u32(self.data, self.header_offset+0, self.image_format.value)
    
    
    write_u32(self.data, self.header_offset+4, self.width)
    write_u32(self.data, self.header_offset+8, self.height)
    write_u8(self.data, self.header_offset+0x14, self.mipmap_count-1)
    
    #write_u8(self.data, self.header_offset+1, self.alpha_setting)
    #write_u8(self.data, self.header_offset+6, self.wrap_s.value)
    #write_u8(self.data, self.header_offset+7, self.wrap_t.value)
    #self.palettes_enabled = self.needs_palettes()
    #write_u8(self.data, self.header_offset+8, int(self.palettes_enabled))
    #write_u8(self.data, self.header_offset+9, self.palette_format.value)
    #write_u16(self.data, self.header_offset+0xA, self.num_colors)
    #write_u32(self.data, self.header_offset+0xC, self.palette_data_offset)
    #write_u8(self.data, self.header_offset+0x14, self.min_filter.value)
    #write_u8(self.data, self.header_offset+0x15, self.mag_filter.value)
    #write_u8(self.data, self.header_offset+0x16, self.min_lod)
    #write_u8(self.data, self.header_offset+0x17, self.max_lod)
    #write_u8(self.data, self.header_offset+0x19, self.unknown_3)
    #write_u16(self.data, self.header_offset+0x1A, self.lod_bias)
    #write_u32(self.data, self.header_offset+0x1C, self.image_data_offset)
  
  @property
  def block_width(self):
    return BLOCK_WIDTHS[self.format]
  
  @property
  def block_height(self):
    return BLOCK_HEIGHTS[self.format]
  
  @property
  def block_data_size(self):
    return BLOCK_DATA_SIZES[self.format]
  
  @property
  def format(self):
    return ImageFormat(TEX_TO_BTI[self.image_format])
  
  def replace_image_from_path(self, new_image_file_path):
    self.image_data, self.palette_data, encoded_colors, self.width, self.height, self.mipmap_count = encode_image_from_path(
      new_image_file_path, self.format, self.palette_format,
      self.width, self.height, mipmap_count=self.mipmap_count
    )
    self.num_colors = len(encoded_colors)
  
  def replace_image(self, new_image):
    self.image_data, self.palette_data, encoded_colors = encode_image(
      new_image, self.format, self.palette_format,
      mipmap_count=self.mipmap_count
    )
    self.num_colors = len(encoded_colors)
    self.width = new_image.width
    self.height = new_image.height
  
  def write_png(self, new_image_file_path):
    print("%s" % self.format)
    image = decode_image(
      self.image_data, self.palette_data,
      self.format, self.palette_format,
      self.num_colors,
      self.width, self.height
    )
    image.save(new_image_file_path + ".png")
    return image

class TexFile(Tex):
  def __init__(self, data, file_entry):
    super(TexFile, self).__init__(data)
    self.file_entry = file_entry
  
  def save_changes(self):
    # Cut off the image and palette data first since we're replacing this data entirely.
    self.data.truncate(0x20)
    self.data.seek(0x20)
    
    self.image_data_offset = 0x20
    self.image_data.seek(0)
    self.data.write(self.image_data.read())
    
    self.save_header_changes()
    self.file_entry.data_size = data_len(self.data)

class TexFileEntry(TexFile):
  def __init__(self, file_entry):
    self.file_entry = file_entry
    super(TexFileEntry, self).__init__(self.file_entry.data, self.file_entry)