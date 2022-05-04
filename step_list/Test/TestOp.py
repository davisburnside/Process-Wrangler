import os
import sys
import random
from random import random
import collections
import time
import string
import importlib
import logging
import bpy
from bpy.props import (IntProperty,
                       BoolProperty,
                       StringProperty,
                       PointerProperty,
                       CollectionProperty)
from bpy.types import (Operator,
                       Panel,
                       PropertyGroup,
                       UIList)
from ... import Helpers 
from ... import Step_Script_Execution 

testvar = "abc"

def get_testvar():
    return testvar