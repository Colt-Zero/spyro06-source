
import os

try:
  from sys import _MEIPASS
  ROOT_PATH = _MEIPASS
  IS_RUNNING_FROM_SOURCE = False
except ImportError:
  ROOT_PATH = os.path.dirname(os.path.realpath(__file__))
  IS_RUNNING_FROM_SOURCE = True

ASSETS_PATH = os.path.join(ROOT_PATH, "assets")
ASM_PATH = os.path.join(ROOT_PATH, "asm")