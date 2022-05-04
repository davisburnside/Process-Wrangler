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
from .. import Step_Script_Execution 


class PROCESSWRANGLER_OT_processVariablesActions(Operator):
    """Move items up and down, add and remove"""
    bl_idname = "processwrangler.process_variables_action"
    bl_label = "Actions"
    bl_description = "Add and remove Execution Variables"
    bl_options  = {'REGISTER', 'UNDO'}

    action: bpy.props.EnumProperty(
        items=(
            ('UP', "Up", ""),
            ('DOWN', "Down", ""),
            ('REMOVE', "Remove", ""),
            ('ADD', "Add", "")))

    # script_names: bpy.props.EnumProperty(items=get_text_name_tuples)
            
    def __init__(self):    
        # executes on any intial Operator interaction
        pass

    def __del__(self):
        # Only executes when canceling a dialog
        pass       

    def execute(self, context):
        
        # Selected value from tuple
        selected_action = self.action
        selected_script_name = context.scene.processwrangler_scripts_in_blend_file
            
#         scn = context.scene
#         idx = scn.processwrangler_step_list_selectedindex
#         exec_ctx = scn.get(Helpers.scene_ctx_name, None)
        
#         try:
#             item = None
#             if len(scn.processwrangler_step_list) > 0:
#                 item = scn.processwrangler_step_list[idx]

#             if self.action == 'DOWN' and idx < len(scn.processwrangler_step_list) - 1:
#                 item_next = scn.processwrangler_step_list[idx + 1].name
#                 scn.processwrangler_step_list.move(idx, idx+1)
#                 scn.processwrangler_step_list_selectedindex += 1
#                 if exec_ctx:
#                     stepnum_first = idx + 1
#                     stepnum_second = idx + 2
#                     Helpers.flag_step_as_reordered(stepnum_first, exec_ctx, scn)
#                     Helpers.flag_step_as_reordered(stepnum_second, exec_ctx, scn)
#                 info = 'Item "%s" moved to position %d' % (item.name, scn.processwrangler_step_list_selectedindex + 1)

#             elif self.action == 'UP' and idx >= 1:
#                 item_prev = scn.processwrangler_step_list[idx - 1].name
#                 scn.processwrangler_step_list.move(idx, idx-1)
#                 scn.processwrangler_step_list_selectedindex -= 1
#                 if exec_ctx:
#                     stepnum_first = idx
#                     stepnum_second = idx + 1
#                     Helpers.flag_step_as_reordered(stepnum_first, exec_ctx, scn)
#                     Helpers.flag_step_as_reordered(stepnum_second, exec_ctx, scn)
#                 info = 'Item "%s" moved to position %d' % (item.name, scn.processwrangler_step_list_selectedindex + 1)

#             elif self.action == 'REMOVE':
#                 info = 'Item "%s" removed from list' % (scn.processwrangler_step_list[idx].name)
#                 scn.processwrangler_step_list.remove(idx)
#                 scn.processwrangler_step_list_selectedindex -= 1
#                 if scn.processwrangler_step_list_selectedindex < 0:
#                     scn.processwrangler_step_list_selectedindex = 0
#                 for post_delete_index, step in enumerate(scn.processwrangler_step_list):
#                     if post_delete_index >= idx and step.step_index_when_previously_executed != -1:
#                         step.step_index_when_previously_executed -= 1

# #                for post_delete_index, step in enumerate(scn.processwrangler_step_list):
# #                    print(post_delete_index, step.step_index_when_previously_executed, step.step_script.name)    
                

#             elif self.action == 'ADD':
#                 item = scn.processwrangler_step_list.add()
#                 item.step_script = bpy.data.texts.get(selected_script_name, None)
                
#                 print("A  :", selected_script_name)
#                 print("B  :", item.step_script)
                
#                 item.step_id = Helpers.generate_step_id()
#                 item.name = item.step_script.name 
#                 scn.processwrangler_step_list_selectedindex = len(scn.processwrangler_step_list) - 1
#                 Helpers.force_redraw_UI(context)
                
#                 # show warning modal if required func is missing
#                 is_valid, error_msg = Helpers.validate_script_has_required_functions(selected_script_name)       
#                 if not is_valid:
#                     scn.processwrangler_cached_msg = error_msg
#                     context.window_manager.popup_menu(Helpers.warning_dialog_with_doc_link)
                    
#             else:
#                 self.report({'INFO'}, "Nothing selected in the Viewport")
                
#         except IndexError:
#             pass
        
#         finally:
            
#             #recalculate step indices 
#             steps_in_order = [x for x in scn.processwrangler_step_list]
#             for index, step in enumerate(steps_in_order):
#                 step.step_index = index
            
        return {"FINISHED"}

    def invoke(self, context, event):
        
        scn = context.scene
        print("invoke")
#         selected_action = self.action
#         if selected_action == "ADD":
#             def draw_script_selection_prompt(self, context):
                
#                 has_text_datablocks = len(bpy.data.texts) > 0
                
#                 layout = self.layout

#                 col = layout.column()
#                 col.label(text="Create Script with PW Template")        
#                 col.operator("processwrangler.create_pw_template_script", icon = "ADD") 
                
#                 if has_text_datablocks:
                
                    
#                     col = layout.column()
#                     col.separator()
#                     row = col.row()
#                     row.label(text="    OR")
#                     col.separator()
#                     col2 = layout.column()
#                     col2.label(text="Choose Existing Script") 
# #                    col2.separator()
# #                    col2.separator()
# #                    col2.prop(scn, "processwrangler_scripts_in_blend_file", text=None, expand=True)    
# #                    col2.separator()
# #                    col2.separator()

#                     # HUGE WTF moment working with this
#                     # I at least know I can "fix" it with expand=False
#                     col2.prop(scn, "processwrangler_scripts_in_blend_file", expand=False, text="")     
#               
        return {"FINISHED"}
        
 