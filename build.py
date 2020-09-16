
from zipfile import ZipFile
import os

from spyro_patcher import VERSION_WITHOUT_COMMIT

base_name = "Spyro06 Patcher"
base_name_with_version = base_name + " " + VERSION_WITHOUT_COMMIT

import struct
if (struct.calcsize("P") * 8) == 64:
  base_name_with_version += "_64bit"
  base_zip_name = base_name_with_version
else:
  base_name_with_version += "_32bit"
  base_zip_name = base_name_with_version

zip_name = base_zip_name.replace(" ", "_") + ".zip"

exe_path = "./dist/%s.exe" % base_name_with_version
if not os.path.isfile(exe_path):
  raise Exception("Executable not found: %s" % exe_path)

with ZipFile("./dist/" + zip_name, "w") as zip:
  zip.write(exe_path, arcname="%s.exe" % base_name)
  zip.write("README.md", arcname="README.txt")
  zip.write("settings.txt", arcname="settings.txt")
  zip.write("./WindowsBuildBatchFiles/Assemble and Patch.bat", arcname="./asm/Assemble and Patch.bat")
  #zip.write("requirements.txt", arcname="requirements.txt")
  zip.write("./WindowsBuildBatchFiles/assemble.bat", arcname="./asm/assemble.bat")
  #zip.write("./asm/assemble.py", arcname="./asm/assemble.py")
  zip.write("./asm/ntsc/linker.ld", arcname="./asm/ntsc/linker.ld")
  zip.write("./asm/ntsc/apply_changes.asm", arcname="./asm/ntsc/apply_changes.asm")
  zip.write("./asm/ntsc/apply_changes_diff.txt", arcname="./asm/ntsc/apply_changes_diff.txt")
  zip.write("./asm/ntsc/custom_funcs.asm", arcname="./asm/ntsc/custom_funcs.asm")
  zip.write("./asm/ntsc/custom_funcs_diff.txt", arcname="./asm/ntsc/custom_funcs_diff.txt")
  #zip.write("./asm/ntsc/remove_optimization_for_freecam.asm", arcname="./asm/ntsc/remove_optimization_for_freecam.asm")
  zip.write("./asm/pal/linker.ld", arcname="./asm/pal/linker.ld")
  zip.write("./asm/pal/apply_changes.asm", arcname="./asm/pal/apply_changes.asm")
  zip.write("./asm/pal/apply_changes_diff.txt", arcname="./asm/pal/apply_changes_diff.txt")
  zip.write("./asm/pal/custom_funcs.asm", arcname="./asm/pal/custom_funcs.asm")
  zip.write("./asm/pal/custom_funcs_diff.txt", arcname="./asm/pal/custom_funcs_diff.txt")
  #zip.write("./asm/pal/remove_optimization_for_freecam.asm", arcname="./asm/pal/remove_optimization_for_freecam.asm")
  zip.write("./WindowsBuildBatchFiles/disassemble.bat", arcname="./disassemble/disassemble.bat")
  zip.write("./WindowsBuildBatchFiles/Extract Raw Files.bat", arcname="./Extract Raw Files.bat")
  zip.write("./WindowsBuildBatchFiles/Extract Textures.bat", arcname="./Extract Textures.bat")
  zip.write("./WindowsBuildBatchFiles/Extract Model Files.bat", arcname="./Experimental/Extract Model Files.bat")
  zip.write("./WindowsBuildBatchFiles/Extract Raw Audio.bat", arcname="./Experimental/Extract Raw Audio.bat")
