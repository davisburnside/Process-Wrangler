import os
import sys
import random
from random import random
import collections
import time
import string
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

class PROCESSWRANGLER_UL_items(UIList):
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        
        scn = context.scene
        split = layout.split(factor=0.5)
        
        # Script 
        split.label(text=item.step_script.name)
        
        # Collection
        row = split.row()
        
        col = row.column()
        button_objs = col.operator("processwrangler.select_col_or_members", icon="OBJECT_DATA", text="")
        button_objs.step_id = item.step_id
        collection = bpy.data.collections.get(item.step_col_name)
        collection_exists_in_scene = collection and scn.user_of_id(collection)
        icon = "OUTLINER_COLLECTION" if collection_exists_in_scene else "COLLECTION_COLOR_01"
        col = row.column()
        button_col = col.label(icon=icon, text="")
        row.alignment = "LEFT"
        col = row.column()
        
        col.alignment = "LEFT"
        col.label(text=item.step_col_name)
        
        # Out-of-order icon
        index_of_prev_exec = item.step_index_when_previously_executed
        if index_of_prev_exec != index + 1 and index_of_prev_exec != -1:
            row.label(icon="FILE_REFRESH")
            
         # Execute? checkbox
        split = layout.split(factor=0.8)
        split.alignment = "RIGHT"
        split.prop(item, "step_enabled", text="")

    def invoke(self, context, event):
        pass   

class PROCESSWRANGLER_PT_ProcessPanel(Panel):

    from .. import Helpers
    
    """Adds a custom panel to the TEXT_EDITOR"""
    bl_idname = "PROCESSWRANGLER_PT_ProcessPanel"
    bl_label = "Process Wrangler"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = 'Process Wrangler'
    # bl_parent_id = "PROCESSWRANGLER_PT_AllSceneProcesses"
    bl_ui_units_x = 10

    execution_result_string: bpy.props.StringProperty() 
    
    def draw(self, context):
        
        layout = self.layout
        scn = bpy.context.scene
        process = scn.processwrangler_data.scene_processes[0]
        exec_ctx = process.get(Helpers.scene_ctx_name, None)
        
        row = layout.row()
        
        # UI List Headers
        col = row.column()
        split = col.split(factor=0.5)
        split.label(text="Script")
        split.label(text="Collection")
        split.alignment = "RIGHT"
        split.label(text="Execute?")

        # UIList
        col.template_list(
            "PROCESSWRANGLER_UL_items", 
            "", 
            process,
            "steps_list",
            process,
            "steps_list_selected_index", 
            rows=2)
        
        # Up/Down and Add/Remove Button Column
        col = row.column(align = True)
        col.ui_units_x = 2
        col.label(text="")
        col.scale_y = 1
        col.operator("processwrangler.list_action", icon='ADD', text="").action = 'ADD'
        col.operator("processwrangler.list_action", icon='REMOVE', text="").action = 'REMOVE'
        col.separator()
        col.separator()
        col.operator("processwrangler.list_action", icon='TRIA_UP', text="").action = 'UP'
        col.operator("processwrangler.list_action", icon='TRIA_DOWN', text="").action = 'DOWN'
        
        row = layout.row()
        row.operator("processwrangler.untag_all_members")
        row = layout.row()
        row.operator("processwrangler.clear_all",)
        row = layout.row()
        row.operator("processwrangler.execute_script_list")
        row.scale_y = 2
        # test = row.operator("wm.properties_edit")
        # test.property_name="prop"
        # test.data_path="scene"
        
        # output execution summary / error msg
        row = layout.row()
        col = row.column()
        run_summary_sting = ""

        cached_msg = scn.processwrangler_data.scene_processes[0].get("processwrangler_cached_msg", None)
        if cached_msg:
                col.alert = True
                error_msg_lines = cached_msg.split("\n")
                _ = [col.label(text=f"    {x}") for x in error_msg_lines]

        elif exec_ctx:
            error_msg = exec_ctx["execution_summary"]["error_message"]
            did_fail = len(error_msg) > 0
            run_summary = exec_ctx["execution_summary"]["run_summary"]
            if did_fail:
                col.alert = True
            col.label(text=run_summary)
            
            # change text color if error occured
            # col.alert = False
            if len(error_msg) > 0:
                error_msg_lines = error_msg.split("\n")
                _ = [col.label(text=f"    {x}") for x in error_msg_lines]

# class PROCESSWRANGLER_PT_AllSceneProcesses(Panel):
    
#     """Debug Panel"""
#     bl_idname = "PROCESSWRANGLER_PT_AllSceneProcesses"
#     bl_label = "Scene Processes"
#     bl_space_type = "VIEW_3D"
#     bl_region_type = "UI"
#     bl_category = 'Process Wrangler'
    

#     def draw(self, context):
        
#         layout = self.layout
#         scn = bpy.context.scene
#         exec_ctx = scn.get(Helpers.scene_ctx_name, None)
        
#         # clear console
#         layout.separator()
#         row = layout.row()
#         row.operator("processwrangler.add_scene_process")   

#         # Print Execution Context
        

#         for process in scn.processwrangler_processes:

#             box = layout.box()
#             row = box.row()

#             print(process)

#             row.menu("PROCESSWRANGLER_PT_ProcessPanel", icon="COLLAPSEMENU")