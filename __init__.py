bl_info = {
    "name": "Process Wrangler",
    "description": "Manage Complex Scenes build with Scripts",
    "author": "Davis Burnside",
    "version": (1, 0, 1),
    "blender": (3, 0, 0),
    "location": "Object Properties",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "User Interface"
}

# Python imports
import os
import sys
import random
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
from . import auto_load
from . import Helpers
from . import PW_Change_Handlers

# print("BLENDER VERSION", bpy.app.version)
if bpy.app.version < (3, 0, 0):
    message = "need version 3.0"
    raise Exception(message)

# This must be called after the declaration of bl_info
# Package name must match addon name
addonName = os.path.basename(os.path.dirname(__file__))
addonVersion = sys.modules[addonName].bl_info["version"]

def get_text_name_tuples(self, context):

    text_name_tuples = [(x.name, x.name, "") for x in list(bpy.data.texts)]
    return text_name_tuples

def script_selected_from_dropdown(scene, context):
    
    bpy.ops.processwrangler.list_action("EXEC_DEFAULT", action="ADD")
    

class PROCESSWRANGLER_step(bpy.types.PropertyGroup):

    step_enabled: BoolProperty(default=True, description="Will this step script be excuted? \nStep Collections will be generated regardless")
    step_script: PointerProperty(type=bpy.types.Text)
    
    # regenerated every execution, even if step is not flagged for execution. 
    # changes based on stepnum and user preference
    step_col_name: StringProperty()
    
    # Random string. set once at step creation & doesn't change, though a "_" character is
    # appened to the ID when it is shuffled in Scrip list.
    step_id: StringProperty()

    # list index, not PW index (offset by the top-level Pw component)
    # this is not changed unless a step is executed
    step_index_when_previously_executed: IntProperty(default = -1)

class PROCESSWRANGLER_process_parameters(bpy.types.PropertyGroup):

    steps_list: CollectionProperty(
        type=PROCESSWRANGLER_step
    )
    steps_list_selected_index: IntProperty()
    cached_msg: StringProperty()
    console_log_level: bpy.props.EnumProperty(
        items=(
            ('DEBUG', "Debug", ""),
            ("INFO", "Info", ""),
            ('WARNING', "Warning", ""),
            ('ERROR', "Error", "")
        ),
        default="DEBUG",
        update=Helpers.update_logger
    )
    console_log_style: bpy.props.EnumProperty(
        items=(
            ("COLORFUL", "Colorful", ""),
            ('MONOCHROME', "Monochrome", "")
        ),
        default="COLORFUL",
        update=Helpers.update_logger
    )
    console_log_tab: bpy.props.IntProperty(
        default=2,
        max = 8,
        min = 0,
        update=Helpers.update_logger
    )
    console_include_step_attachments: bpy.props.BoolProperty(
        default=True,
        update=Helpers.update_logger
    )
    console_include_prev_step: bpy.props.BoolProperty(
        default=True,
        update=Helpers.update_logger,
        description="Include data from previous run?"
    )

class PROCESSWRANGLER_process_data(bpy.types.PropertyGroup):

    active_scene_process_index: bpy.props.IntProperty(default=0)
    scene_processes: CollectionProperty(type=PROCESSWRANGLER_process_parameters)

    # used in "Add Script" popup Panel
    #==============================
    scripts_in_blend_file: bpy.props.EnumProperty(
        description="",
        items=get_text_name_tuples,
        update=script_selected_from_dropdown,
        default=None)

def register():
    
    print(f"Installing {addonName} version {addonVersion}")

    # Automatically finds, imports, & registers Blender classes in a nested directory stack :D
    auto_load.init()
    auto_load.register()
    
    bpy.utils.register_class(PROCESSWRANGLER_step)
    bpy.utils.register_class(PROCESSWRANGLER_process_parameters)
    bpy.utils.register_class(PROCESSWRANGLER_process_data)

    bpy.types.Scene.processwrangler_data = bpy.props.PointerProperty(
        type=PROCESSWRANGLER_process_data,
        name = "PW Data"
        )


    print("Registered Process Wrangler")
    print("V18")

    if len(bpy.context.scene.processwrangler_data.scene_processes) == 0:
        bpy.ops.processwrangler.add_scene_process()
        
def unregister():

    auto_load.unregister()
        
    # if hasattr(bpy.types.Scene, "processwrangler_step_list_selectedindex"):
    #     del bpy.types.Scene.processwrangler_step_list_selectedindex
    # if hasattr(bpy.types.Scene, "processwrangler_step_list"):
    #     del bpy.types.Scene.processwrangler_step_list
    # if hasattr(bpy.types.Scene, "processwrangler_cached_msg"):
    #     del bpy.types.Scene.processwrangler_cached_msg 
    # if hasattr(bpy.types.Scene, "processwrangler_console_log_level"):
    #     del bpy.types.Scene.processwrangler_console_log_level    
    # if hasattr(bpy.types.Scene, "processwrangler_console_log_style"):
    #     del bpy.types.Scene.processwrangler_console_log_style  
    # if hasattr(bpy.types.Scene, "processwrangler_console_log_tab"):
    #     del bpy.types.Scene.processwrangler_console_log_tab
    # if hasattr(bpy.types.Scene, "processwrangler_console_include_step_attachments"):
    #     del bpy.types.Scene.processwrangler_console_include_step_attachments
    # if hasattr(bpy.types.Scene, "processwrangler_console_include_prev_step"):
    #     del bpy.types.Scene.processwrangler_console_include_prev_step
    # if hasattr(bpy.types.Scene, "processwrangler_execution_variables"):
    #     del bpy.types.Scene.processwrangler_execution_variables
    # if hasattr(bpy.types.Scene, "processwrangler_scene_processes"):
    #     del bpy.types.Scene.processwrangler_scene_processes
    # if hasattr(bpy.types.Scene, "processwrangler_scene_processes"):
    #     del bpy.types.Scene.processwrangler_active_process_index
    
    
    bpy.utils.unregister_class(PROCESSWRANGLER_process_data)     
    bpy.utils.unregister_class(PROCESSWRANGLER_process_parameters)
    bpy.utils.unregister_class(PROCESSWRANGLER_step)
    PW_Change_Handlers.unregister()

    print("Unregistered Process Wrangler")

if __name__ == "__main__":
    register()