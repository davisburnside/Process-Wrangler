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
from .. import Scene_Wiping 

def get_text_name_tuples(self, context):
    
    text_name_tuples = [(x.name, x.name, x.name) for x in list(bpy.data.texts)]
    return text_name_tuples

def get_steps_execution_override(scene, process):
    
    steps_list = process.steps_list
    shuffled_steps = [(x[1].step_index_when_previously_executed != -1 and x[0] != x[1].step_index_when_previously_executed) for x in enumerate(steps_list)]
    enabled_steps = [x.step_enabled for x in steps_list]
    steps_execution_override = [shuffled_steps[idx] and not enabled_steps[idx] for idx in range(len(steps_list))]
    steps_execution_override = [x[0] + 1 for x in enumerate(steps_execution_override) if x[1]]
    return shuffled_steps, steps_execution_override


class PROCESSWRANGLER_OT_newSceneProcess(Operator):
    """Create new Process"""
    bl_idname = "processwrangler.add_scene_process"
    bl_label = "Add Process"
    bl_description = "Add Process"
    bl_options = {'REGISTER', 'UNDO'}
            
    # @classmethod
    # def poll(cls, context):
    #     if context.mode != "OBJECT":
    #         cls.poll_message_set("ONLY AVAILABLE IN OBJECT MODE")
    #     return context.mode == "OBJECT"

        
    def execute(self, context):     
        
        scn = context.scene
        new_process = scn.processwrangler_data.scene_processes.add()
        return {"FINISHED"}   

class PROCESSWRANGLER_OT_executeScriptList(Operator):
    """Execute Process scripts in descending order"""
    bl_idname = "processwrangler.execute_script_list"
    bl_label = "Execute Process"
    bl_description = "Execute Process scripts in descending order"
    bl_options = {'REGISTER', 'UNDO'}
            
    @classmethod
    def poll(cls, context):
        if context.mode != "OBJECT":
            cls.poll_message_set("ONLY AVAILABLE IN OBJECT MODE")
        return context.mode == "OBJECT"

    def invoke(self, context, event):
        
        scn = context.scene
        process = scn.processwrangler_data.scene_processes[0]
        
        # Check if any shuffled scripts are deactivated.
        # If so, warn the user that they will need to be executed one time
        exec_ctx_exists = scn.get(Helpers.scene_ctx_name)
        _, steps_execution_override = get_steps_execution_override(scn, process)
        if exec_ctx_exists and len(steps_execution_override) > 0:
            string_beginning = f"Steps {' & '.join(map(str, steps_execution_override))} have" if len(steps_execution_override) > 1 else f"Step {steps_execution_override[0]} has"    
            warning_message = f"{string_beginning} been shuffled and needs to be re-executed. Continue?"
            def draw_prompt(self, context):
                layout = self.layout
                layout.label(text=warning_message)
                layout.separator()
                layout.operator("processwrangler.execute_script_list")

            context.window_manager.popup_menu(draw_prompt)
            return {"FINISHED"}
        
        else:
            
            def draw_prompt(self, context):
                    layout = self.layout
                    layout.label(text=warning_message)

            # Check if any steps are defined
            all_steps = process.steps_list
            if len(all_steps) == 0:
                warning_message = "No steps are defined. Click the + icon to add a new one"
                context.window_manager.popup_menu(draw_prompt)
                return {"FINISHED"}
                
            # Check if all scripts are deactivated.
            all_enabled_steps = [x for x in all_steps if x.step_enabled]
            if len(all_enabled_steps) == 0:
                warning_message = "No scripts are enabled. Nothing will happen during execution"
                context.window_manager.popup_menu(draw_prompt)
                return {"FINISHED"}
                
            else:   
                
                # Execute script sequence
                return self.execute(context)
        
    def execute(self, context):     
        
        scn = context.scene
        process = scn.processwrangler_data.scene_processes[0]
        
        # determine logging level & style to use
        ui_logging_level = process.console_log_level
        map_log_level = {
            "DEBUG" : logging.DEBUG,
            "INFO" : logging.INFO,
            "WARNING" : logging.WARNING,
            "ERROR" : logging.ERROR,
        }
        logging_level = map_log_level[ui_logging_level]
        logging_style = process.console_log_style
        logging_tab_len = process.console_log_tab
        
        # determine scripts that need to be executed anyway (both disabled & shuffled)
        exec_stc_exists = scn.get(Helpers.scene_ctx_name)
        _, steps_execution_override = get_steps_execution_override(scn, process)
        if not exec_stc_exists or len(steps_execution_override) == 0:
            steps_execution_override = None
 
        # Execute script
        #============================
        did_execute, error_msg = Step_Script_Execution.PW_execute(
            context, 
            process,
            steps_execution_override, 
            logging_level, 
            logging_style, 
            logging_tab_len)  
        #============================
        
        process["processwrangler_cached_msg"] = error_msg
        
        if did_execute:

            # update Collection labels in UIList
            all_steps = process.steps_list
            exec_cxt = scn.get(Helpers.scene_ctx_name)
            for index, step in enumerate(all_steps):
                if exec_cxt:
                    col_names = exec_cxt["current_execution_data"]["step_collection_names"]
                    steps_did_execute = exec_cxt["current_execution_data"]["step_did_execute"]
                    
                    #remove first entry- it is not part of the List
                    steps_did_execute = steps_did_execute[1:]
                    col_names = col_names[1:]

                    if len(col_names) > index:
                        
                        # save name of new collection
                        step.step_col_name = col_names[index]
                        
                        # save the stepnum that this step was last executed at
                        if steps_did_execute[index]:
                            step.step_index_when_previously_executed = index
                        
        return {"FINISHED"}    

class PROCESSWRANGLER_OT_selectCollectionOrMembers(Operator):
    """Select objects generated by process step"""
    bl_idname = "processwrangler.select_col_or_members"
    bl_label = ""
    bl_description = "Select objects generated by process step"
    bl_options = {'REGISTER', 'UNDO'}

    step_id: bpy.props.StringProperty()
    
    @classmethod
    def poll(cls, context):
        if context.mode != "OBJECT":
            cls.poll_message_set("ONLY AVAILABLE IN OBJECT MODE")
        return context.mode == "OBJECT"

    def execute(self, context):
        
        scn = context.scene
        exec_ctx = scn.get(Helpers.scene_ctx_name)
        if exec_ctx:
            Helpers.select_collection_objects_for_stepnum(self.step_id, exec_ctx, context)
            self.step_id = ""
        
        return {"FINISHED"}    

class PROCESSWRANGLER_OT_untagAllPWMembers(Operator):
    """Remove PW tags for all scene members"""
    bl_idname = "processwrangler.untag_all_members"
    bl_label = "Untag All"
    bl_description = "Remove PW tags for all scene members"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        if context.mode != "OBJECT":
            cls.poll_message_set("ONLY AVAILABLE IN OBJECT MODE")
        return context.mode == "OBJECT"

    def invoke(self, context, event):

        def draw_prompt(self, context):
            layout = self.layout
            layout.label(text="If you untag PW Step Collections, you must manually delete them before executing this Process again.")
            layout.operator_context = "EXEC_DEFAULT"
            layout.operator("processwrangler.untag_all_members", text="Continue")
        context.window_manager.popup_menu(draw_prompt)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        
        Helpers.PW_untag_all(context.scene)
        return {"FINISHED"}    

class PROCESSWRANGLER_OT_clearAll(Operator):
    """Clear All Process Outputs"""
    bl_idname = "processwrangler.clear_all"
    bl_label = "Clear Process Output"
    bl_description = "Clear Everything that was generated by Process Wrangler"
    bl_options = {'REGISTER', 'UNDO'}
            
    @classmethod
    def poll(cls, context):
        if context.mode != "OBJECT":
            cls.poll_message_set("ONLY AVAILABLE IN OBJECT MODE")
        return context.mode == "OBJECT"

    def invoke(self, context, event):
        
        return self.execute(context)
        
    def execute(self, context):
        
        scn = context.scene
        process = scn.processwrangler_data.scene_processes[0]
        
        # clear cached values in UI & disable "Select Objects" button
        for step in process.steps_list:
            step.step_col_name = ""
            step.step_index_when_previously_executed = -1

        # clear PW objects, collections, orphaned data, and scene properties
        Scene_Wiping.PW_scene_clear_all(context.scene)
          
        return {"FINISHED"}    

class PROCESSWRANGLER_OT_createPWTemplateScript(Operator):
    """Create New Script With Process Wrangler Template"""
    bl_idname = "processwrangler.create_pw_template_script"
    bl_label = "New Script"
    bl_description = "Create New Script With Process Wrangler Template"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        
        # Generate new Text file, write the template to it
        new_text = bpy.data.texts.new(name="PW Template")
        
        text_lines = Helpers.get_pw_template_script_body()
        for line in list(text_lines.splitlines()):
            new_text.write(f"{line}\n")
        
        # Add the Script as a PW step
        # A listener attached to this variable will trigger new step creation
        context.scene.processwrangler_data.scripts_in_blend_file = new_text.name
        
        # show the file in the UI
        # If there is a UI, (not being run windowless from CMD), 
        # choose the biggest Text-editor scene in the UI window.
        try:
            if (bpy.context.window_manager
                and bpy.context.window_manager.windows
                and len(bpy.context.window_manager.windows) > 0):
                max_area = 0
                area_to_switch = None
                for area in context.screen.areas:
                    if area.type == "TEXT_EDITOR":
                        total_area = area.width * area.height
                        if total_area > max_area:
                            area_to_switch = area
                            max_area = total_area
                
                if area_to_switch and len(area_to_switch.spaces) > 0:
                    area_to_switch.spaces[0].text = bpy.data.texts[new_text.name]
        except:
            pass

        return {"FINISHED"}    

class PROCESSWRANGLER_OT_listActions(Operator):
    """Move items up and down, add and remove"""
    bl_idname = "processwrangler.list_action"
    bl_label = "List Actions"
    bl_description = "Move items up and down, add and remove"
    bl_options  = {'REGISTER', 'UNDO'}

    action: bpy.props.EnumProperty(
        items=(
            ('UP', "Up", ""),
            ('DOWN', "Down", ""),
            ('REMOVE', "Remove", ""),
            ('ADD', "Add", "")))

    script_names: bpy.props.EnumProperty(items=get_text_name_tuples)
            
    def __init__(self):    
        # executes on any intial Operator interaction
        pass

    def __del__(self):
        # Only executes when canceling a dialog
        pass       

    def execute(self, context):
        
        
        scn = context.scene
        process = scn.processwrangler_data.scene_processes[0]
        selected_action = self.action
        selected_script_name = scn.processwrangler_data.scripts_in_blend_file
        idx = process.steps_list_selected_index
        exec_ctx = scn.get(Helpers.scene_ctx_name, None)
        
        try:
            item = None
            if len(process.steps_list) > 0:
                item = process.steps_list[idx]

            if self.action == 'DOWN' and idx < len(process.steps_list) - 1:
                item_next = process.steps_list[idx + 1].name
                process.steps_list.move(idx, idx+1)
                process.steps_list_selected_index += 1
                if exec_ctx:
                    stepnum_first = idx + 1
                    stepnum_second = idx + 2
                    Helpers.flag_step_as_reordered(stepnum_first, exec_ctx, scn)
                    Helpers.flag_step_as_reordered(stepnum_second, exec_ctx, scn)
                info = 'Item "%s" moved to position %d' % (item.name, process.steps_list_selected_index + 1)

            elif self.action == 'UP' and idx >= 1:
                item_prev = process.steps_list[idx - 1].name
                process.steps_list.move(idx, idx-1)
                process.steps_list_selected_index -= 1
                if exec_ctx:
                    stepnum_first = idx
                    stepnum_second = idx + 1
                    Helpers.flag_step_as_reordered(stepnum_first, exec_ctx, scn)
                    Helpers.flag_step_as_reordered(stepnum_second, exec_ctx, scn)
                info = 'Item "%s" moved to position %d' % (item.name, process.steps_list_selected_index + 1)

            elif self.action == 'REMOVE':
                info = 'Item "%s" removed from list' % (process.steps_list[idx].name)
                process.steps_list.remove(idx)
                process.steps_list_selected_index -= 1
                if process.steps_list_selected_index < 0:
                    process.steps_list_selected_index = 0
                for post_delete_index, step in enumerate(process.steps_list):
                    if post_delete_index >= idx and step.step_index_when_previously_executed != -1:
                        step.step_index_when_previously_executed -= 1

            elif self.action == 'ADD':
                item = process.steps_list.add()
                item.step_script = bpy.data.texts.get(selected_script_name, None)
                item.step_id = Helpers.generate_step_id()
                item.name = item.step_script.name 
                process.steps_list_selected_index = len(process.steps_list) - 1
                Helpers.force_redraw_UI(context)
                
                # show warning modal if required func is missing
                is_valid, error_msg = Helpers.validate_script_has_required_functions(selected_script_name)       
                if not is_valid:
                    process.processwrangler_data.cached_msg = error_msg
                    context.window_manager.popup_menu(Helpers.warning_dialog_with_doc_link)
                    
            else:
                self.report({'INFO'}, "Nothing selected in the Viewport")
                
        except IndexError:
            pass
        
        finally:
            
            #recalculate step indices 
            steps_in_order = [x for x in process.steps_list]
            for index, step in enumerate(steps_in_order):
                step.step_index = index
            
        return {"FINISHED"}

    def invoke(self, context, event):
        
        scn = context.scene
        selected_action = self.action
        if selected_action == "ADD":

            def draw_script_selection_prompt(self, context):
                
                has_text_datablocks = len(bpy.data.texts) > 0
                layout = self.layout
                col = layout.column()
                col.label(text="Create Script with PW Template")        
                col.operator("processwrangler.create_pw_template_script", icon = "ADD") 
                if has_text_datablocks:
                    col = layout.column()
                    col.separator()
                    row = col.row()
                    row.label(text="    OR")
                    col.separator()
                    col2 = layout.column()
                    col2.label(text="Choose Existing Script") 
#                    col2.separator()
#                    col2.separator()
#                    col2.prop(scn, "processwrangler_scripts_in_blend_file", text=None, expand=True)    
#                    col2.separator()
#                    col2.separator()

                    # HUGE WTF moment working with this
                    # I at least know I can "fix" it with expand=False
                    col2.prop(scn.processwrangler_data, "scripts_in_blend_file", expand=False, text="")     
#               
            context.window_manager.popup_menu(draw_script_selection_prompt)
            return {"FINISHED"}
        
        else:
            return self.execute(context)       