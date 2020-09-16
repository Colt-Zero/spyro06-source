# -*- mode: python -*-

block_cipher = None

with open("./version.txt") as f:
  patcher_version = f.read().strip()

import struct
if (struct.calcsize("P") * 8) == 64:
  patcher_version += "_64bit"
else:
  patcher_version += "_32bit"

import os
import glob
def build_datas_recursive(paths):
  datas = []
  
  for path in paths:
    for filename in glob.iglob(path, recursive=True):
      dest_dirname = os.path.dirname(filename)
      if dest_dirname == "":
        dest_dirname = "."
      
      data_entry = (filename, dest_dirname)
      datas.append(data_entry)
      print(data_entry)
  
  return datas

a = Analysis(['spyro_patcher.py'],
             pathex=[],
             binaries=[],
             datas=build_datas_recursive([
               'assets/**/*.*',
               'data/*.txt',
               'logic/*.txt',
               'seedgen/*.txt',
               'version.txt',
             ]),
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='Spyro06 Patcher ' + patcher_version,
          debug=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=True,
          icon="assets/icon.ico" )
