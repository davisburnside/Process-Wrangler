import ssl
import os
import sys
import random
import collections
import time
import json
import traceback
import logging
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
from . Helpers import *
from . Scene_Wiping import *

class ExecutionContextWrapper():

    exec_vars: None
    
    exec_ctx: None

    #=========================================================
    # Class functions

    def __init__(self, exec_ctx, exec_vars=None):
        self.vars = exec_vars
        self.exec_ctx = exec_ctx

    def __getitem__(self, item):

        # allow class to be subsribable
         return self.exec_ctx[item]

    #=========================================================
    # Util functions

    def is_jsonable(self, x):
        try:
            json.dumps(x)
            return True
        except (TypeError, OverflowError) as e:
            print(e)
            return False

    def pretty_json(self, dict):
        parsed = json.dumps(dict, indent=4)
        return parsed

    def add_blend_file_to_syspath(self, print_full_syspath=False):

        logger = self.get_logger()
        dir_path = os.path.dirname(bpy.data.filepath)
        if dir_path not in sys.path:
            logger.warning("Adding '{dir_path}' to sys.path")
            sys.path.append(dir_path)
            if print_full_syspath:
                logger.info('Full Path:')
                _ = [logger.info(x) for x in sys.path]

    def remove_blend_file_to_syspath(self, print_full_syspath=False):

        logger = self.get_logger()
        dir_path = os.path.dirname(bpy.data.filepath)
        do_log = True
        while dir_path in sys.path:
            if do_log:
                logger.warning("Removing '{dir_path}' from sys.path")
                do_log = False
            sys.path.remove(dir_path)
        if print_full_syspath:
            logger.info('Full Path:')
            _ = [logger.info(x) for x in sys.path]

    # def make_collection_visible_to_view_layer(self, col_name, vl_name, exclusive=False):

    #     if not bpy.data.collections.get(col_name):
    #         raise Exception(f"Collection '{col_name}' does not exist")
    #     if not bpy.context.scene.view_layers.get(vl_name):
    #         raise Exception(f"View Layer '{vl_name}' does not exist in Scene '{bpy.context.scene.name}'")

    #     # for view_layer in bpy.context.scene.view_layers:

    #     if exclusive:
    #         for view_layer in bpy.context.scene.view_layers:
    #             col = view_layer.layer_collection.children[col_name]
    #             col.exclude = True

    #     view_layer = bpy.context.scene.view_layers[vl_name]
    #     print([x.name for x in view_layer.layer_collection.children])
    #     col = view_layer.layer_collection.children[col_name]
    #     col.exclude = False


                    

    #     # def include_only_one_collection(view_layer: bpy.types.ViewLayer, collection_include: bpy.types.Collection):
    #         for layer_collection in view_layer.layer_collection.children:
    #             if layer_collection.collection != collection_include:
    #                 layer_collection.exclude = True
    #             else:
    #                 layer_collection.exclude = False

    # # if __name__ == "__main__":
    #     view_layer = bpy.context.scene.view_layers["View Layer"]
    #     collection_include = bpy.data.collections["Collection"]
    #     include_only_one_collection(view_layer, collection_include)

    #=========================================================
    # Data getters

    def get_logger(self):

        # logger = get_logger()
        return logging.getLogger(Helpers.PW_logger_name)

    def get_process_id(self):
        return 0

    def get_current_stepnum(self):

        return self.exec_ctx["current_execution_data"]["current_step"]

    def get_current_step_data(self):

        stepnum = self.get_current_stepnum()
        return self.get_step_data_from_identifier(stepnum)

    def get_step_data_from_identifier(self, step_identifier):

        stepnum = None
        step_id = None
        col_name = None
        script_name = None
        did_execute = None
        attached_data = None
        ctx_data = self.exec_ctx["current_execution_data"]

        # if the identifier is the stepnum
        if isinstance(step_identifier, int):
            if step_identifier < 0:
                return None, f"Invalid step number ({step_identifier})"
            if len(ctx_data["step_ids"]) < step_identifier:
                return None, f"step number ({step_identifier}) does not exist in this context"
            
            stepnum = step_identifier
            script_name = ctx_data["step_script_names"][stepnum]
            col_name = ctx_data["step_collection_names"][stepnum]
            step_id = ctx_data["step_ids"][stepnum]
            did_execute = ctx_data["step_did_execute"][stepnum]
            attached_data = ctx_data["step_attached_data"][stepnum]

        # if the identifier is the step id
        elif isinstance(step_identifier, str):
            all_step_ids = [x["step_ids"] for x in ctx_data].insert(0, pw_master_collection_name_id)
            if step_identifier not in all_step_ids:
                return None, f"step ID ({step_identifier}) does not exist in current context"
            step_id = step_identifier
            stepnum = [x[0] for x in enumerate(ctx_data["step_ids"]) if x[1] == step_id][0]
            script_name = ctx_data["step_script_names"][stepnum]
            col_name = ctx_data["step_collection_names"][stepnum]
            did_execute = ctx_data["step_did_execute"][stepnum]
            attached_data = ctx_data["step_attached_data"][stepnum]

        return stepnum, step_id, script_name, col_name, did_execute, attached_data

    def get_all_objects_from_step(self, step_identifier):

        _, step_id, _, _, _, _ = self.get_step_data_from_identifier(step_identifier)
        objects = Helpers.get_PW_tagged_for_step("objects", tag_name=Helpers.PW_tag_generated, step_id = step_id)
        return objects

    def get_exec_var(self, key):

        logger = self.get_logger()
        if not key in self.exec_vars.keys():
            msg = f"Variable {key} not found"
            logger.error(msg)
            return None, f"Variable {key} not found"
        return self.exec_vars[key]

    #=========================================================
    # Data attachment handling

    def get_attached_data_by_key(self, key, only_data=True, only_first=True):

        # Format:
        # [
        #   [
        #       "key": key,
        #       "contents": data dict,
        #       "tags": [tag1, tag2, ...] ,
        #       "step_id": step id ,
        #       "step_num": step number
        #   ],
        #    ...
        # ]
        return_data = []
        data_all_steps = self.exec_ctx["current_execution_data"]["step_attached_data"]
        ids_all_steps = self.exec_ctx["current_execution_data"]["step_ids"]
        for index, step_data in enumerate(data_all_steps):
            step_id = ids_all_steps[index]
            for data_key in step_data:
                if data_key == key:
                    data_chunk = {
                        "key": data_key,
                        "contents": step_data[key]["contents"],
                        "tags": step_data[key]["tags"],
                        "step_id": step_id,
                        "step_num": index
                    }
                    return_data.append(data_chunk)

        if only_first:
            return_data =  return_data[0] if len(return_data) > 0 else None

        if only_data:
            return_data = return_data["contents"]
        
        return return_data

    def get_attached_data_by_tag(self, tag, only_first=False):

        # Format:
        # [
        #   [
        #       "key": key,
        #       "contents": data dict,
        #       "tags": [tag1, tag2, ...] ,
        #       "step_id": step id ,
        #       "step_num": step number
        #   ],
        #    ...
        # ]
        return_data = []
        data_all_steps = self.exec_ctx["current_execution_data"]["step_attached_data"]
        ids_all_steps = self.exec_ctx["current_execution_data"]["step_ids"]
        for index, step_data in enumerate(data_all_steps):
            step_id = ids_all_steps[index]
            for data_key in step_data:
                data = step_data[data_key]
                for data_tag in data["tags"]:
                    if data_tag == tag:
                        data_chunk = {
                            "key": data_key,
                            "contents": step_data[data_key]["contents"],
                            "tags": step_data[data_key]["tags"],
                            "step_id": step_id,
                            "step_num": index
                        }
                        return_data.append(data_chunk)

        if only_first:
            return return_data[0] if len(return_data) > 0 else None        
        return return_data

    def attach_data(self, key, data, tags=None, enforce_new = False):

        logger = Helpers.get_logger()
        
        # Since the Execution Context is saved as a Scene Property, everything in it needs to be serializable
        if not self.is_jsonable(data):
            logger.error("Attached data must be serialized")
            return None

        # enforce tags array format
        if isinstance(tags, str):
            tags = [tags]
        if not tags:
            tags = []
        try:
            
            # enforces uniqueness, ensures listability
            tags = set(tags)
            tags = list(tags)
        except:
            raise Exception("Tags list is an invalid format: {tags.__class__}")

        # invalid_tags = [x for x in tags if not isinstance(x, str)]
        # if len(invalid_tags)> 0:
        #     raise Exception(f"Data tags must be a string. Invalid tags: {invalid_tags}")

        # attach data to exec_ctx
        stepnum = self.get_current_stepnum()
        step_data_array = self.exec_ctx["current_execution_data"]["step_attached_data"]
        current_step_data_chunks = step_data_array[stepnum]

        if enforce_new and current_step_data_chunks.get(key):
            error_msg = f"Unable to attach data with key '{key}' to step {stepnum}. Key already exists in step data array and enforce_new=True"
            raise Exception(error_msg)
        else:
            logger.debug(f"Attaching data with key '{key}' to step {stepnum}")
            if len(tags) > 0:
                logger.debug(f"This data is tagged with ")
            step_data_chunk = {
                "tags": tags,
                "contents": data #if isinstance(data, dict) else json.dumps(data),
            }
            current_step_data_chunks[key] = step_data_chunk
