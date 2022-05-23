import os
import sys
import random
from random import random
import collections
import time
import string
import importlib
import logging
import json
import bpy
import subprocess 

from bpy.props import (IntProperty,
                       BoolProperty,
                       StringProperty,
                       PointerProperty,
                       CollectionProperty)
from bpy.types import (Operator,
                       Panel,
                       PropertyGroup,
                       UIList)
from .. import Helpers 
from .. import Scene_Wiping 

def exec_ctx_to_str(exec_ctx, process):

    if not exec_ctx:
        return None
    
    # configured in debug panel
    tab_size = process.console_log_tab
    include_step_attached_data = process.console_include_step_attachments
    include_prev_step = process.console_include_prev_step
    
    # remove unwanted parts
    exec_ctx_dict = exec_ctx.to_dict()
    if not include_step_attached_data:              
        dicts = [exec_ctx_dict["previous_execution_data"].get("step_attached_data", None), exec_ctx_dict["current_execution_data"]["step_attached_data"]]
        for dict in dicts:
            if dict:
                for step_data in dict:
                    for step_data_key in step_data:
                        step_data[step_data_key]["contents"] = "..."
    if not include_prev_step:
        try:
            del exec_ctx_dict["previous_execution_data"]
        except:
            pass
    
    # stringify
    exec_cxt_str = json.dumps(exec_ctx_dict, indent=tab_size)
    return exec_cxt_str

#=====================================================
  
class PROCESSWRANGLER_OT_clearConsole(Operator):
    """Clear Console"""
    bl_idname = "processwrangler.clear_console"
    bl_label = "Clear Console"
    bl_description = "Clear Console"
    
    def execute(self, context):
        
        if os.name == "nt":
            os.system("cls") 
        else:
            os.system("clear") 

        return {"FINISHED"}    

#=====================================================

class PROCESSWRANGLER_OT_printExecutionContext(Operator):
    """Print Execution Context for Process"""
    bl_idname = "processwrangler.print_exec_ctx"
    bl_label = "Print to Console"
    bl_description = "Print Execution Context for Process"
    
    def execute(self, context):
        
        scn = context.scene
        process = scn.processwrangler_data.scene_processes[0]
        exec_ctx = process.get(Helpers.scene_ctx_name, None)
        
        #bypass logging, use print instead
        if exec_ctx:      
            print(f"\n{exec_ctx_to_str(exec_ctx, process)}\n")
        else:
            print(f"No Execution Context found in scene '{scn.name}'. You must execute a process first.")
          
        return {"FINISHED"}   

#=====================================================
    
class PROCESSWRANGLER_OT_copyExecutionContextToClipboard(Operator):
    """Copy to Console"""
    bl_idname = "processwrangler.copy_to_clipboard"
    bl_label = "Copy to Clipboard"
    bl_description = "Copy to Clipboard"
    
    def execute(self, context):
        
        scn = context.scene
        process = scn.processwrangler_data.scene_processes[0]
        exec_ctx = process.get(Helpers.scene_ctx_name, None)
        exec_ctx_str = exec_ctx_to_str(exec_ctx, process)
        bytes = exec_ctx_str.encode('utf-8')
        if sys.platform == 'win32' or sys.platform == 'cygwin':
            subprocess.Popen(['clip'], stdin=subprocess.PIPE).communicate(bytes)
        else:
            raise Exception('Platform not supported')
            
        return {"FINISHED"}    
