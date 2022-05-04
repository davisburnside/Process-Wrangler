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
from .. import Helpers

class PROCESSWRANGLER_PT_DebugPanel(Panel):
    
    """Debug Panel"""
    bl_idname = "PROCESSWRANGLER_PT_DebugPanel"
    bl_label = "Console Tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = 'Process Wrangler'
    bl_parent_id = "PROCESSWRANGLER_PT_ProcessPanel"
    bl_order = 2

    def draw(self, context):
        
        layout = self.layout
        scn = bpy.context.scene
        exec_ctx = scn.get(Helpers.scene_ctx_name, None)
        
        # clear console
        layout.separator()
        row = layout.row()
        # row.scale_y = 1.5
        row.operator("processwrangler.clear_console")   

        # Print Execution Context
        box = layout.box()
        row = box.row()
        row.label(text="View Excution Context")
        # off center for some reason
        # row.alignment = "CENTER"
        box.operator("processwrangler.print_exec_ctx")
        box.operator("processwrangler.copy_to_clipboard")
        row = box.row()
        row.prop(scn, "processwrangler_console_include_step_attachments", text="Include Step-Attached Data?")
        # row.label(text=)
        row = box.row()
        row.prop(scn, "processwrangler_console_include_prev_step", text="Include Prev. Exec. Data?")
        # row.label(text="Include Prev. Exec. Data?")
        
        # bottom section
        box = layout.box()
        row = box.row()
        split = row.split(factor=0.5)
        # Left column
        col = split.column()
        row = col.row()
        col.label(text="Log Level")
        col.prop(scn, "processwrangler_console_log_level", expand=True)
        # Right column
        col = split.column()
        row = col.row()
        col.label(text="Log Style")
        col.prop(scn, "processwrangler_console_log_style", expand=True)
        col.separator()
        split = col.split(factor=0.4)
        split.prop(scn, "processwrangler_console_log_tab", text="")
        split.label(text="Tab Size")
