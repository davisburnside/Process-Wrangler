import ssl
import os
import sys
import random
import collections
import time
import json
import traceback
import logging
import string
from enum import Enum
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
from . import Helpers 
from . import Scene_Wiping 
from . import Execution_Context_Wrapper 

def pretty_error_msg(e):
    pass

def note_screen_image_contents(context, space_imageeditors):

    for area in context.screen.areas:
        if area.type == 'IMAGE_EDITOR':
            for space in area.spaces:
                if space.type == 'IMAGE_EDITOR' and space.image:
                    space_imageeditors.append((space, space.image.name, space.zoom))

def restore_screen_image_contents(step_id, space_imageeditors):

    new_images = Helpers.get_PW_tagged_for_step("images", tag_name=Helpers.PW_step_id_tag, step_id=step_id)
    for (space, space_image_name, zoom) in space_imageeditors:
        
        # unknown if the space object will be invalid by this line-
        # If a user's script modifies the UI, this may be a problem
        try:
            if space_image_name in [x.name for x in new_images] and (not space.image or space.image.name != space_image_name):
                space.image = bpy.data.images.get(space_image_name)
                # not working. Why?
                space.zoom = zoom
        except:
            pass

def PW_execute(
    context, 
    process,
    execution_override_steps = None, 
    log_level=logging.DEBUG, 
    log_style="COLORFUL", 
    tab_length = 2):

    if not execution_override_steps:
        execution_override_steps = []

    space_imageeditors = []
    scene = context.scene
    prev_exec_ctx = scene.get(Helpers.scene_ctx_name)
    prev_exec_ctx = prev_exec_ctx.to_dict() if prev_exec_ctx else None
    exec_ctx = None
    should_save_exec_ctx_to_scene = True
    try:

        # configure logging
        logger = Helpers.get_logger()
        Helpers.config_logger_for_PW(logger, log_level, log_style, tab_length)

        logger.warning("")
        logger.warning('============== Begin Process Execution ==============')
        logger.warning("")

        # Get data from Process Step list shown in UI
        raw_scripts_list = [
            {
            "text_block_name": x.step_script.name, 
            "step_id": x.step_id,
            "is_enabled": x.step_enabled
            }
            for x in process.steps_list]
        scripts_list_indexed = [
            {
            "stepnum": x[0] + 1, # top-level step is already defined
            "text_block_name": x[1]["text_block_name"], 
            "step_id": x[1]["step_id"],
            "is_enabled": x[1]["is_enabled"]
            }
            for x in enumerate(raw_scripts_list)]

        # Remove old execution context if it is invalid
        if not Helpers.is_exec_ctx_valid(scene.get(Helpers.scene_ctx_name)):
            logger.warning("Invalid execution context in Scene. Making a new one")
            Helpers.PW_scene_clear_all(scene)

        # Generate fresh PW execution context
        exec_ctx = Helpers.generate_execution_context()
        exec_ctx["current_execution_data"]["current_step"] = 0 
        exec_ctx["current_execution_data"]["execution_result"] = "STARTED" 

        # add PW Master collection if it does not exist anywhere in the scene (will create nothing if parent_col already exist)
        # This allows users to put the master PW Collection as a child of any other collections
        top_level_col_id = Helpers.pw_master_collection_name_id
        if Helpers.pw_master_collection_name not in [x.name for x in bpy.data.collections]:
            pw_master_col = Helpers.create_PW_step_collection(top_level_col_id, Helpers.pw_master_collection_name)
        else:
            pw_master_col = bpy.data.collections[Helpers.pw_master_collection_name]
            
        # Clean up remnants from previous execution if needed
        # pw_master_col must exist before this step
        Scene_Wiping.eliminate_PW_orphans(scene, exec_ctx)

        # prev_step_data is used to track parent-child relationships of process steps
        # only one child step exists per parent
        prev_step_data = {
            "col_name": Helpers.pw_master_collection_name, 
            "script_name": __name__}

        # Validate Scripts and Collections for all steps
        # Also compile final step data array
        block_process_execution = False
        complete_step_data_array = []
        for step_data in scripts_list_indexed:
            stepnum = step_data["stepnum"]
            script_name = step_data["text_block_name"]
            should_execute = step_data["is_enabled"]
            step_id = step_data["step_id"]

            # allow steps to be executed even if not selected in the UI
            if stepnum in execution_override_steps:
                should_execute = True

            # Ensure that Text datablocks are valid scripts
            # Getting the named text datablock will execute it when loaded
            #  as a module, so ensure code is wrapped inside functions
            text_datablock= bpy.data.texts.get(script_name)
            if not text_datablock:
                raise Exception(f"Text Datablock named {script_name} does not exist")

            # Validate script contents
            script_module = None
            module_error = None
            try:
                script_module = text_datablock.as_module() 
                if Helpers.processWrangler_execute_func_name not in list(dir(script_module)):
                    function_signature = f"{Helpers.processWrangler_execute_func_name}(exec_ctx)"
                    module_error = f"Script '{text_datablock.name}' is missing a required function '{function_signature}'"
                    block_process_execution = True
            except Exception as e: 
                
                where_error = f"Compile error in Script '{script_name}' at Step {stepnum} "
                module_error = f"{where_error}\n{str(e)}"
                block_process_execution = True

            # Determine the names of each step outputs in process
            # If any naming conflicts exists, prompt the user to rename collections
            # Collection name depends on step number & user preference
            col_name = Helpers.get_col_name_of_step_script(stepnum, script_module)
            existing_col = bpy.data.collections.get(col_name, False)
            if existing_col and not Helpers.is_PW_tagged(existing_col):
                raise Exception(f"Non-PW-tagged Collection '{col_name}' already exists \nRename or delete it to resolve name conflict")

            # Build final step data array 
            complete_step_data_array.append({
                "stepnum": stepnum,
                "step_id": step_id,
                "should_execute": should_execute,
                "script_name": script_name,
                "col_name": col_name,
                "text_datablock": text_datablock,
                "script_module": script_module,
                "module_error": module_error
            })

        if block_process_execution:
            should_save_exec_ctx_to_scene = False
            errors = [x["module_error"] for x in complete_step_data_array if x["module_error"]]
            errors = "\n\n".join(errors)
            # traceback.print_stack()
            return False, errors

        # If steps have been reordered, execution must happen for all steps after the highest-changed step
        # IE: If steps 3 & 4 changed places, everything after step 2 must be reexecuted
        if exec_ctx and exec_ctx["previous_execution_data"].get("step_ids"):
            previous_step_ids = exec_ctx["previous_execution_data"]["step_ids"]
            current_step_ids = [x["step_id"] for x in complete_step_data_array]
            first_changed_step = -1
            for index in range(len(previous_step_ids)):
                if len(previous_step_ids) < index or len(current_step_ids) < index:
                    break
                if previous_step_ids[index] != current_step_ids[index]:
                    first_changed_step = index + 1
                    break
            if first_changed_step != -1:
                for x in complete_step_data_array:
                    if int(x["stepnum"]) >= first_changed_step:
                        x["should_execute"] = True

        # the root process step will not be examined in the loop below, so do it here
        child_col_name = complete_step_data_array[0]["col_name"]
        child_step_id = complete_step_data_array[0]["step_id"]
        # all_step_ids = [x["step_id"] for x in complete_step_data_array]
        if Helpers.step_col_validate_children(pw_master_col, child_col_name, child_step_id):
            
            # set execution flag for first step
            scripts_list_indexed[0]["is_enabled"] = True

            _ = [Scene_Wiping.delete_PW_step_collection(x.name, scene, False) for x in pw_master_col.children]
        
        # Execute scripts / generate collections in sequential order
        last_stepnum = len(complete_step_data_array)
        
        for step_data in complete_step_data_array:
            stepnum = step_data["stepnum"]
            step_id = step_data["step_id"]
            should_execute = step_data["should_execute"]
            script_name = step_data["script_name"]
            col_name = step_data["col_name"]
            text_datablock = step_data["text_datablock"]
            script_module = step_data["script_module"]
            module_error = step_data["module_error"]

            # Steps need to have Collections, even if a step script isn't executed
            parent_col_name = prev_step_data["col_name"]
            parent_col = bpy.data.collections[parent_col_name]
            step_col = bpy.data.collections.get(col_name, None)
            if not step_col:
                step_col = Helpers.create_PW_step_collection(step_id, col_name, Helpers.pw_master_collection_name)

            # Validate children
            # if stepnum != last_stepnum:
            #     child_col_name = complete_step_data_array[stepnum]["col_name"]
            #     child_step_id = complete_step_data_array[stepnum]["step_id"]
            #     if Helpers.step_col_validate_children(step_col, child_col_name, child_step_id):

            #         # set execution flag for first step
            #         should_execute = True
                    
            #         # #delete Collection & Collection members of first-level children
            #         _ = [Scene_Wiping.delete_PW_step_collection(x.name, scene, False) for x in step_col.children]

            # append step data to execution context (Not saved to Scene until process completes)
            exec_ctx["current_execution_data"]["step_script_names"].append(script_name)
            exec_ctx["current_execution_data"]["step_collection_names"].append(col_name)
            exec_ctx["current_execution_data"]["step_ids"].append(step_id)
            exec_ctx["current_execution_data"]["step_did_execute"].append(should_execute)
            exec_ctx["current_execution_data"]["step_attached_data"].append({})
            exec_ctx["current_execution_data"]["current_step"] = stepnum
            
            if should_execute:

                # Check if the PW execution function is present in the file. The script can't be evaluated without it
                if script_module and Helpers.processWrangler_execute_func_name in list(dir(script_module)):
                    
                    logger.info(f"executing step {stepnum}")

                    # clear old stuff, make new stuff
                    Scene_Wiping.delete_PW_step_collection(col_name, scene, include_children = True, include_col=False)
                    # original_col_children_names = [x.name for x in step_col.children]
                    # _ = [Scene_Wiping.delete_PW_step_collection(x.name, scene, False) for x in parent_col.children]

                    # new Collections takes over parentage of children from previous executions
                    # If the child steps are flagged for execution though, the children will be replaced in later steps
                    # for child_col_name in original_col_children_names:
                    #     child_col = bpy.data.collections.get(child_col_name)
                    #     if child_col and child_col_name not in [x.name for x in step_col.children]:
                    #         step_col.children.link(child_col)

                    # get 'before' snapshot for tagging new objects 
                    scene_snapshot_before_step = Helpers.snapshot_scene_objects(scene)

                    # execute main function of module
                    # 'ProcessWrangler_execute' function of script
                    try:
                        # Wrapping the exec_ctx allows utility functions to be added to it
                        exec_ctx_wrapper = Execution_Context_Wrapper.ExecutionContextWrapper(exec_ctx)

                        # Images generated by PW will need to be manually set back into image editor screens if they are active there 
                        note_screen_image_contents(context, space_imageeditors)              

                        ###########################################################################################
                        # Execute Process
                        processWrangler_execute = getattr(script_module, Helpers.processWrangler_execute_func_name)
                        processWrangler_execute(exec_ctx_wrapper)
                        ###########################################################################################

                    # Errors occuring inside script are logged to console, saved to exec_ctx, and displayed in UI
                    except BaseException as e:

                        where_error = f"Error while executing script '{script_name}' at step {stepnum}"
                        logger.error(where_error)

                        # print concise error details, format & remove unnecessary information
                        # Softens the blow, I guess
                        error_stack = traceback.format_exc().split('\n')
                        start_line = 3
                        max_line_count = 50
                        error_stack = error_stack[start_line:max_line_count + start_line]
                        if len(error_stack) > 0:
                            error_stack[0] = error_stack[0].replace("File \"<string>\",", "", 1)
                            error_stack[0] = error_stack[0].strip()
                        error_stack.insert(0, str(type(e)))
                        error_stack[0], error_stack[1]  = error_stack[1], error_stack[0] 
                        final_error_str = "\n".join(error_stack)

                        # contains stack trace up to max_line_count lines long
                        logger.error(final_error_str)

                        where_error = f"In script '{script_name}' at step {stepnum} "
                        final_error_str = f"{where_error}\n{final_error_str}"

                        # Exit execution loop if python error occurs
                        exec_ctx["execution_summary"]["error_message"] = final_error_str
                        exec_ctx["current_execution_data"]["execution_result"] = "EXECUTION FAILED" 
                        break

                    finally:
                        
                        # tag new objects
                        scene_snapshot_after_step = Helpers.snapshot_scene_objects(scene)
                        Helpers.tag_PW_generated_objects(step_col, scene_snapshot_before_step, scene_snapshot_after_step, scene)
                        scene_snapshot_before_step = scene_snapshot_after_step
                        logger.info(f"finished step {stepnum}")

                        # Images generated by PW will need to be manually set back into image editor screens if they are active there 
                        restore_screen_image_contents(step_id, space_imageeditors)

                # Check if the Script failed evaluation (likely because of compilation error)
                elif script_module is None:

                    error_str = f"Could not evaluate Script '{script_name}' at step {stepnum}\n{module_error}"

                    # Exit execution loop if python error occurs
                    exec_ctx["execution_summary"]["error_message"] = error_str
                    exec_ctx["current_execution_data"]["execution_result"] = "EXECUTION FAILED" 
                    logger.error(error_str) 
                    break

                # Script is flagged as belonging to a Process Step, but missing the required execution function         
                else:
                    # function_signature = f"{Helpers.processWrangler_execute_func_name}(exec_ctx)"
                    # error_str = f"Script '{text_datablock.name}' is missing a required function '{function_signature}'"

                    # # Exit execution loop if python error occurs
                    # exec_ctx["execution_summary"]["error_message"] = error_str
                    # exec_ctx["current_execution_data"]["execution_result"] = "EXECUTION FAILED" 
                    # logger.error(error_str)
                    print("THIS SHOULDN'T BE HERE 1")
                    break

            else:
                logger.info(f"skipping execution for step {stepnum}")

                # copy attached data from previous run
                # all_prev_step_attachment_arrays = prev_exec_ctx["previous_execution_data"].get("step_attached_data")
                # print(all_prev_step_attachment_arrays)
                # print(Helpers.pretty_json(exec_ctx["previous_execution_data"]))
                # if all_prev_step_attachment_arrays and len(all_prev_step_attachment_arrays) >= stepnum:
                #     prev_step_attachments_array = all_prev_step_attachment_arrays[stepnum]
                #     exec_ctx["current_execution_data"]["step_attached_data"][stepnum] = prev_step_attachments_array
                #     logger.debug(f"Copied attached data for step {stepnum} from previous exection ({len(prev_step_attachments_array)} items)")

            # Log step result, populate quick cache 
            prev_step_data["col_name"] = col_name
            prev_step_data["script_name"] = script_name
            if stepnum == last_stepnum and exec_ctx["current_execution_data"]["execution_result"] == "STARTED":
                exec_ctx["current_execution_data"]["execution_result"] = "FINISHED SUCCESSFULLY"
                logger.info("Process completed")
                            
        exec_ctx["current_execution_data"]["end_time"] = str(round(time.time() * 1000))

        # bpy.context.view_layer.objects.active = None
        # bpy.ops.object.select_all(action="DESELECT")

        logger.warning("")
        logger.warning('=============== End Process Execution ===============')
        logger.warning("")

    except BaseException as e:
        exec_ctx["execution_summary"]["error_message"] = str(e)
        exec_ctx["current_execution_data"]["execution_result"] = "EXECUTION FAILED" 
        logger.error(e)
    finally:
        if should_save_exec_ctx_to_scene:
            Helpers.save_exec_cxt(exec_ctx, scene)
            return True, None
