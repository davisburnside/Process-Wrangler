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
from . Scene_Wiping import *
from . Execution_Context_Wrapper import *

# PW variables
#========================================================================
pw_master_collection_name = "Process Wrangler Output"
pw_master_collection_name_id = "A1"
scene_ctx_name = "pw exec ctx"
processWrangler_execute_func_name = "step_execute"
PW_tag_generated = "PW step generated"
PW_step_id_tag = "PW step id"
PW_col_procstep_tag = "PW ProcStep"
PW_len_stepid = 24
PW_logger_name = "Process Wrangler Log"

# tags applyable to Objects, Collections, Meshes, etc.
# Scene variables not included (scene_ctx_name)
all_PW_tags = [PW_col_procstep_tag, PW_step_id_tag, PW_tag_generated]

# Datablock types that can be tagged & manipulated by Process Wrangler
# Any inheritor of bpy.types.ID can theoretically be used, but I haven't tried them all
PW_db_types = [
    "collections",
    "objects",
    "meshes",
    "curves",
    "images",
    "materials",
    "textures",
    "node_groups"
]

#========================================================================
# UI Interaction 



# def warning_dialog_with_doc_link(self, context):
    
#     layout = self.layout
    
#     msg = context.scene.processwrangler_cached_msg
#     row = layout.row()
    
#     layout.alert = True
#     row.label(text=msg)
#     row.alert = True

#=========================================================
# Logging 

class ColoredFormatter(logging.Formatter):

    # Custom Log format, configurable colors & tab size
    # Courtesy of Sergey Pleshakov
    # stackoverflow.com/questions/384076/how-can-i-color-python-logging-output

    def __init__(self, format_str, tab_length=2, use_color=True):
        self.format_str = format_str
        self.tab_len = tab_length
        self.use_color = use_color
        tab_str = (" " * self.tab_len) if self.tab_len > 0 else ""
        if self.use_color:
            self.FORMATS = {
                logging.DEBUG: self.OKBLUE + tab_str * 3 + format_str + self.reset,
                logging.INFO: self.grey + tab_str * 2 + format_str + self.reset,
                logging.WARNING: self.yellow + tab_str * 1 + format_str + self.reset,
                logging.ERROR: self.red + format_str + self.reset,
                logging.CRITICAL: format_str
            }
        else:
            self.FORMATS = {
                logging.DEBUG: tab_str * 3 + format_str,
                logging.INFO: tab_str * 2 + format_str,
                logging.WARNING: tab_str * 1 + format_str,
                logging.ERROR: format_str,
                logging.CRITICAL: format_str 
            }

    tab_len=True 
    use_color=True

    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    underline = "'\033[4m'"
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format_str = "%(message)s"
    FORMATS = {}
    
    # executed every log entry
    def format(self, record):

        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

def config_logger_for_PW(logger, level, style, tabs):

    reset_logging(logger)
    format_string= "%(message)s"
    logger = logging.getLogger(PW_logger_name)
    logger.propagate = False
    logger.setLevel(level)

    # remove all existing Handlers
    while len(logger.handlers) > 0:
        logger.handlers.pop()
    streamhdlr = logging.StreamHandler(sys.stdout)

    # add new Handler
    if style == "COLORFUL":
        streamhdlr.setFormatter(ColoredFormatter(format_string, tab_length=tabs, use_color=True))
    else:
        streamhdlr.setFormatter(ColoredFormatter(format_string, tab_length=tabs, use_color=False))
        # formatter = logging.Formatter(format_string)
        # streamhdlr.setFormatter(formatter)

    logger.addHandler(streamhdlr)

def update_logger(self, context):
    
    level = context.scene.processwrangler_console_log_level
    style = context.scene.processwrangler_console_log_style
    tabs = context.scene.processwrangler_console_log_tab
    logger = Helpers.get_logger()
    Helpers.config_logger_for_PW(logger, level, style, tabs)

def reset_logging(logger):

    # from stackoverflow.com/questions/12034393/import-side-effects-on-logging-how-to-reset-the-logging-module
    # Courtesy of Eugene Pakhomov

    manager = logging.root.manager
    manager.disabled = logging.NOTSET
    if isinstance(logger, logging.Logger):
        logger.setLevel(logging.NOTSET)
        logger.propagate = True
        logger.disabled = False
        logger.filters.clear()
        handlers = logger.handlers.copy()
        for handler in handlers:
            # Copied from `logging.shutdown`.
            try:
                handler.acquire()
                handler.flush()
                handler.close()
            except (OSError, ValueError):
                pass
            finally:
                handler.release()
            logger.removeHandler(handler)

def get_logger(trick=False):

    return logging.getLogger(PW_logger_name)

#==========================================================
# Utility 

def traverse_tree(t):

    yield t
    for child in t.children:
        yield from traverse_tree(child)

def get_all_PW_tagged_pretty_str(datablock_types = PW_db_types, tag_name=PW_tag_generated):

    dict = get_names_of_PW_tagged_things(PW_db_types, tag_name)

    # Dict to pretty string
    pretty_json_str = pretty_json(dict)
    return pretty_json_str

def get_step_id_variants(step_id):

    if not step_id:
        return
    step_id_with_change_flag = step_id if step_id[-1] == "_" else f"{step_id}_"
    step_id_without_change_flag = step_id[0:-1] if step_id[-1] == "_" else step_id
    return [step_id_with_change_flag, step_id_without_change_flag]

def select_collection_objects_for_stepnum(step_id, exec_ctx, bpy_ctx):
    
    step_id_variants = get_step_id_variants(step_id)
    if not step_id_variants:
        return

    # select only objects tagged with the selected step id.
    # This will select objects even if their original colleciton is gone
    bpy.ops.object.select_all(action='DESELECT')
    col_objects_all_steps = get_PW_tagged("objects", PW_step_id_tag)
    col_objects = [x for x in col_objects_all_steps if x[PW_step_id_tag] in step_id_variants]
    for object in col_objects:
        object.select_set(True)
        bpy_ctx.view_layer.objects.active = object

def generate_step_id():
    
    step_id = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(PW_len_stepid))
    return step_id

def generate_execution_context():

    # These arrays will always have the same length:
    # (step_script_names, step_collection_names, step_ids, step_did_execute)

    # Execution data for the top-level Script / Container (The file this addon is defined in, pw_master_collection_name) 
    # will also be included in the exec_ctx,  though it is not likely to be useful

    # Int data, like timestamps, must be stored as a String. This because they are converted toC-types
    # upon saving to the Scene & the timestamps are too big of an Integer

    logger = get_logger()
    logger.info("generating new execution context")
    exec_cxt = {
        "current_execution_data" : {
            "current_step": "-1",
            "execution_result": "NOT STARTED",
            "start_time" : str(round(time.time() * 1000)),
            "end_time" : "0",
            "step_script_names" : [__name__],    
            "step_collection_names" : [pw_master_collection_name],  
            "step_ids" : [pw_master_collection_name_id],
            "step_did_execute" : [True],  
            "step_attached_data": [{}]
        },
        "previous_execution_data" : {},
        "execution_summary" : {
            "run_summary" : "",
            "error_message" : ""
        }
    }

    return exec_cxt

def get_pw_template_script_body():
    
    text_body = '''
import random
import bpy

step_description = "My Step"

def step_execute(exec_ctx):

    # Access data through Execution Context
    step_num = exec_ctx.get_current_stepnum()
    msg = f"Hello from step {step_num}"

    # Logging settings are configured under the "Debugging" panel
    logger = exec_ctx.get_logger()
    logger.info(msg)
    
    # Add new Object
    bpy.ops.object.text_add(location = (0, 0, step_num-1))
    obj = bpy.context.object
    obj.data.body = msg
    
    # Randomize its appearance
    bpy.ops.object.modifier_add(type='WAVE')
    obj.modifiers["Wave"].start_position_x = random.uniform(0, 7)
    obj.modifiers["Wave"].start_position_y = random.uniform(-1, 1)
    '''
    return text_body

def randstring():
    return_string = "".join(list([random.choice(string.ascii_letters) for i in range(3)]))
#    return_string = ""
    return return_string 

def pretty_json(dict):

    parsed = json.dumps(dict, indent=4)
    return parsed

def is_windows_system():
    return sys.platform in ["win32"]

def force_redraw_UI(context):
    
    for region in context.area.regions:
        if region.type == "UI":
            region.tag_redraw()

#==========================================================
# Getters

def get_prev_exec_steps(exec_ctx):
    return exec_ctx["previous_execution_data"]["step_script_names"], exec_ctx["previous_execution_data"]["step_collection_names"]

def get_all_PW_cols():
    return [c.name for c in bpy.data.collections if bpy.context.scene.user_of_id(c) and is_PW_tagged(c)]

def is_col_procstep_owned(col):
    
    if col.get(PW_col_procstep_tag, False):
        return True
    return False

def get_stepnum_of_procstep_col(col):
        
    if col.get(PW_tag_generated) is None:
        raise Exception(f"No PW step data inside Collection '{col.name}'")
    
    return int(col[PW_tag_generated])

def get_data_for_stepnum(stepnum, exec_ctx, use_previous=False):

    data = exec_ctx["current_execution_data"] if not use_previous else exec_ctx["previous_execution_data"]
    
    if len(data["step_script_names"]) < stepnum:
        return None, None, None
    
    script_name = data["step_script_names"][stepnum]
    step_col_name = data["step_collection_names"][stepnum]
    step_id = data["step_ids"][stepnum]

    return script_name, step_col_name, step_id

def get_col_name_of_step_script(stepnum, script_module):

    # if not script_module or "step_description" not in list(dir(script_module)):
    #     return str(f"Step {stepnum}")
    # else:
    #     return str(f"Step {stepnum}: {script_module.step_description}")
    return str(f"Step {stepnum}")

def get_col_parent(col):
    parent_lookup = {}
    for col in traverse_tree(col):
        for key in col.children.keys():
            parent_lookup.setdefault(key, col.name)
    return parent_lookup

def get_names_of_PW_tagged_things(datablock_types = PW_db_types, tag_name=PW_tag_generated):
    
    if isinstance(datablock_types, str):
        datablock_types = [datablock_types]
    
    # create nested dict of datablock names & the names of their respective PW-tagged members
    return_dict = {}
    for datablock_type in datablock_types:
        # datablock = getattr(bpy.data, datablock_type)
        tagged_member_names = [x.name for x in get_PW_tagged(datablock_type, tag_name)]
        # print(datablock_type, "??????", tagged_member_names)
        # traceback.print_stack()
        return_dict[datablock_type] = tagged_member_names

    return return_dict

def get_datablock(datablock_name, scene):

    if datablock_name in PW_db_types:
        return getattr(bpy.data, datablock_name)
    else:
        raise Exception(f"invalid datablock type: '{datablock_name}'")

def get_PW_tagged(datablock_type, tag_name=PW_tag_generated):
    
    # validation
    datablock_type = datablock_type.lower()
    if not datablock_type or datablock_type not in PW_db_types:
        raise Exception(str(f"Wrong type ({datablock_type}): you must specify a valid datablock type in {PW_db_types}"))
  
    # get tagged objects (python objects, not blender objects)
    target_datablocks = getattr(bpy.data, datablock_type)
    all_in_scene = [x for x in target_datablocks]
    all_PW_tagged= [x for x in all_in_scene if is_PW_tagged(x, tag_name)]
    return all_PW_tagged

def get_PW_tagged_for_step(datablock_type, tag_name=PW_tag_generated, step_id = None):
    
    if not step_id:
        return
    step_id_variants = get_step_id_variants(step_id)
    if not step_id_variants:
        return

    all_PW_tagged = get_PW_tagged(datablock_type, tag_name)       
    step_PW_tagged = [x for x in all_PW_tagged if x[PW_step_id_tag] in step_id_variants]
    return step_PW_tagged

#==========================================================
# Setters

def save_exec_cxt(new_exec_cxt, scene):
    
    # write previous execution context data to the new one
    previous_exec_ctx = scene.get(scene_ctx_name)
    if previous_exec_ctx:
        for field_name in previous_exec_ctx["current_execution_data"].keys():
            previous_value = previous_exec_ctx["current_execution_data"][field_name]
            new_exec_cxt["previous_execution_data"][field_name] = previous_value
        
    # make a summary of run events
    run_time = int(new_exec_cxt["current_execution_data"]["end_time"]) - int(new_exec_cxt["current_execution_data"]["start_time"])
    did_fail = new_exec_cxt["current_execution_data"]["execution_result"] != "FINISHED SUCCESSFULLY"
    execution_run_summary = f"Process {0} execution completed succesfully in {run_time} ms" if not did_fail else "Process {0} execution failed"
    new_exec_cxt["execution_summary"]["run_summary"] = execution_run_summary

    # save some execution data to the scene
    scene[scene_ctx_name] = new_exec_cxt

    get_logger().debug("saved execution context to scene")

def snapshot_scene_objects(scene):

    # snapshots are taken before and after each process step.
    # snapshots are used to identify & tag objects created by each step
    
    #Format of snapshot:
    # {
    #     "collections" : <Set of bpy.data.collections>,
    #     "objects" : <Set of bpy.data.objects>,
    #     "meshes" : <Set of bpy.data.meshes>,
    #     ...
    # }

    snapshot = {}
    for datablock_type_name in PW_db_types:
        datablock = get_datablock(datablock_type_name, scene)
        all_datablock_member_names = {x.name for x in datablock}
        snapshot[datablock_type_name] = all_datablock_member_names
    return snapshot

def tag_PW_generated_objects(col_step, snapshot_before_step, snapshot_after_step, scene):
    
    step_id = col_step[PW_step_id_tag]
    for datablock_type in snapshot_before_step:
        datablock = get_datablock(datablock_type, scene)
        new_members = snapshot_after_step[datablock_type] - snapshot_before_step[datablock_type]
        _ = [PW_tag(datablock.get(x), step_id) for x in new_members]

        # link new objects to correct collections
        if datablock_type == "objects":
            for obj_name in new_members:
                obj = bpy.data.objects.get(obj_name)
                if obj:
                    unlink_obj_from_all_cols(obj)
                    col_step.objects.link(obj)
    
def PW_tag(thing, step_id = None):

    logger = get_logger()
    try:
        logger.debug(f"Tag {thing.bl_rna.name} '{thing.name}' with step id {step_id}")
        thing[PW_tag_generated] = "1"
        if step_id:
            thing[PW_step_id_tag] = step_id
    except:
        logger.error(f"Failed to tag {thing.bl_rna.name} '{thing.name}' with step id {step_id}")

def PW_untag_all(scene):

    logger = get_logger()
    dict = get_names_of_PW_tagged_things()
    logger.debug("Untagging all PW members: ", dict)
    for datablock_type in dict:
        datablock = Helpers.get_datablock(datablock_type, scene)
        for datablock_member in Helpers.get_PW_tagged(datablock_type):
            for tag_name in all_PW_tags:
                if is_PW_tagged(datablock_member, tag_name):
                    try:
                        # Maybe trigger user-customized change listeners? Not sure
                        datablock_member[tag_name] = None
                        del datablock_member[tag_name]
                    finally:
                        pass

def unlink_obj_from_all_cols(obj):
    
    for col in obj.users_collection[:]:  
        # if not is_PW_tagged(col): 
        col.objects.unlink(obj)

def create_PW_step_collection(step_id, col_name, parent_col_name=None, exec_ctx=None):

    logger = get_logger()

    # Validation
    if parent_col_name and not bpy.data.collections.get(parent_col_name, False):

        # There are a few edge cases where the parent might not exist- such as if
        # the user is disabling & reordering scripts in a certain sequence between executions
        # attempt to fix the hierarchy. If not possible, raise an exception
        
        # determine if parent of parent can be identified
        if exec_ctx:
            pass
        raise Exception(f"Parent Collection with name '{parent_col_name}' does not exist")
    
    # If col already exists, return it instad of creating it again
    col = bpy.data.collections.get(col_name, False)
    parent_col = bpy.data.collections.get(parent_col_name, None) if parent_col_name is not None else None
    if col and is_PW_tagged(col) and parent_col_name in get_col_parent(col):
        return col
    
    # Create new Collection, tag, and link to Scene & Parent Collection
    new_procstep_col = bpy.data.collections.new(col_name)

    # If no parent Collection is specified, the new Collection will be a top-level child of the Scene
    if parent_col:
        # stepnum = get_stepnum_of_procstep_col(parent_col) + 1
        parent_col.children.link(new_procstep_col)
        logger.debug(f"Making new collection '{col_name}' with parent '{parent_col_name}'")
    else:
        bpy.context.scene.collection.children.link(new_procstep_col)
        logger.debug(f"Making new collection '{col_name}'")
        
    # tag Collection as PW-generated
    PW_tag(new_procstep_col, step_id=step_id)

    # In addition to normal PW tag, Collections owned by process steps recieve an additional tag
    new_procstep_col[PW_col_procstep_tag] = True
    return new_procstep_col

def flag_step_as_reordered(stepnum, exec_ctx, scene):

    print("FLAG ========================== flag_step_as_reordered")

    _, _, step_id = get_data_for_stepnum(stepnum, exec_ctx)
    all_step_members = get_names_of_PW_tagged_things()
    for datablock_type in all_step_members:
        datablock = get_datablock(datablock_type, scene)
        tagged_members = [x for x in get_PW_tagged(datablock_type, PW_step_id_tag)]
        for member in tagged_members:
            if member[PW_step_id_tag] == step_id and step_id[1 : None] != "_":
                member[PW_step_id_tag] = f"{member[PW_step_id_tag]}_"

#==========================================================
# Verification

def validate_script_has_required_functions(script_name):
    
    text_datablock = bpy.data.texts.get(script_name)
    if not text_datablock:
        return False, f"Text file named {script_name} does not exist"
    
    func_name = Helpers.processWrangler_execute_func_name
    proper_function_signature = f"{func_name}(exec_ctx)"
    txt_content_function_signature = f"def {func_name}"
    text_lines = text_datablock.lines
    for line in text_lines:
        sig_length = len(txt_content_function_signature)
        if len(line.body) >= sig_length and line.body[0:(sig_length)] == txt_content_function_signature:
            return True, None
        
    function_signature = f"{Helpers.processWrangler_execute_func_name}(exec_ctx)"
    error_str = f"Script '{script_name}' is missing a required function with signature '{function_signature}' "
    return False, error_str

def step_col_validate_children(col_step, col_child_step_name, child_step_id, rename_if_needed=True):
    
    # print(col_step, col_child_step_name, child_step_id, rename_if_needed)

    logger = get_logger()

    pw_tagged_children_cols = [x for x in col_step.children if is_col_procstep_owned(x)]
    num_parent_children = len(pw_tagged_children_cols)

    if num_parent_children == 0:
        return False
    
    col_child = bpy.data.collections.get(col_child_step_name, None)
 
    has_invalid_children = (col_child_step_name and pw_tagged_children_cols[0].name != col_child_step_name)
    
    # if num_parent_children == 2 and (col_child_step_name and pw_tagged_children_cols[0].name != col_child_step_name):

    if has_invalid_children:

        # If the user has renamed a script, rename the collection instead of deleting it
        invalid_col_step_id = pw_tagged_children_cols[0].get(PW_step_id_tag)
        if (rename_if_needed 
            and len(pw_tagged_children_cols) == 1
            and invalid_col_step_id == child_step_id):
            logger.debug(f"changing name of Collection '{pw_tagged_children_cols[0].name}' to '{col_child_step_name}'")
            pw_tagged_children_cols[0].name = col_child_step_name
            return False

        logger.debug(f"Collection {col_step.name} has invalid children")
    
    return has_invalid_children

def is_exec_ctx_valid(exec_ctx):
    
    try:
        
        # Does execution context exist with correct formatting?
        if not exec_ctx:
            return False
        
            # Does execution context have scripts & associated collections?
        if (
            len(exec_ctx["current_execution_data"]["step_script_names"]) == 0 
            or len(exec_ctx["current_execution_data"]["step_collection_names"]) == 0
            or len(exec_ctx["current_execution_data"]["step_script_names"]) != len(exec_ctx["current_execution_data"]["step_collection_names"])
            ):
            return False
        
    except:
        
        return False
    
    return True

def is_PW_tagged(obj, tag_name=PW_tag_generated):
    
    return obj.get(PW_tag_generated, False)
