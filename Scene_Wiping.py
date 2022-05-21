import bpy
import os
import sys
import random
import collections
import time
import json
from enum import Enum
from . import Helpers

def remove_thing(thing, type, scene):

    logger = Helpers.get_logger()
    logger.debug(f"Delete '{thing.name}' from {type}")
    datablock = Helpers.get_datablock(type, scene)
    datablock.remove(thing, do_unlink=True)

def eliminate_PW_orphans(scene = None, exec_ctx = None):

    logger = Helpers.get_logger()

    # Top level collection (Process Wrangler Output)
    # must be generated before this step
    top_level_parent_col = bpy.data.collections[Helpers.pw_master_collection_name]
    dict = Helpers.get_names_of_PW_tagged_things()
    logger.debug("Removing orphaned members. All PW members: ", dict)
    for datablock_type in dict:
        datablock = Helpers.get_datablock(datablock_type, scene)
        for datablock_member in Helpers.get_PW_tagged(datablock_type):

            # Remove PW Objects with no scene membership
            if datablock_type == "objects":
                object_scene_membership = [x for x in datablock_member.users_scene]
                if len(object_scene_membership) == 0:
                    logger.debug(f"Tagged Object {datablock_member.name} has no scene membership")
                    remove_thing(datablock_member, datablock_type, scene)

            # top_level_parent_col.children_recursive is only availble in blender 3.1+ 
            # remove PW Collections that don't belong to a step 
            # if datablock_type == "collections":

            #     step_ids = 

            #     # is_in_child_hierarchy = datablock_member in top_level_parent_col.children_recursive
            #     if datablock_member != top_level_parent_col:# and not is_in_child_hierarchy:
            #         # logger.debug(f"Collection {datablock_member} is not a child of anything, deleting")
            #         remove_thing(datablock_member, datablock_type, scene)

            else:
                pass
                # if thing.
            # Remove datablocks with no users

def PW_scene_clear_all(scene):

    logger=Helpers.get_logger()
    logger.info("clearing all Process Wrangler results")

    # cycle through all datablocks that inherit from bpy.types.ID
    for datablock_type_name in Helpers.PW_db_types:
        datablock = Helpers.get_datablock(datablock_type_name, scene)
        for db_member in datablock:
            if Helpers.is_PW_tagged(db_member):
                remove_thing(db_member, datablock_type_name, scene)
                # datablock.remove(db_member, do_unlink=True)

    # clear Execution Context data from Scene 
    all_scene_PW_ctx_props = [Helpers.scene_ctx_name, "processwrangler_cached_msg"]
    for cust_prop in all_scene_PW_ctx_props:
        if scene.get(cust_prop, False):
            del scene[cust_prop]

def delete_PW_step_collection(col_name, scene, include_children=True, include_col = True):

    logger = Helpers.get_logger()

    if not bpy.data.collections.get(col_name, False):
        logger.warning(f"cannot delete Collection {col_name}, it doesn't exist")
        return

    col_step = bpy.data.collections[col_name]
    step_id_to_delete = col_step[Helpers.PW_step_id_tag]

    # if children collections & their objects should also be removed, execute this func recursively (depth-first)
    if include_children:
        for child_col in col_step.children:
            delete_PW_step_collection(child_col.name, scene, include_children)

    logger.debug(f"Delete Collection {col_name} and Objects. Also delete child hierarchy? {include_children}") 
    
    dict = Helpers.get_names_of_PW_tagged_things()
    for datablock_type in dict:

        # cycle through all datablocks that inherit from bpy.types.ID
        datablock = Helpers.get_datablock(datablock_type, scene)
        for datablock_member in Helpers.get_PW_tagged(datablock_type):
            
            # remove any PW tagged objects missing a step Id (unsure when this would happen)
            # member_has_step_id = datablock_member.get(Helpers.PW_step_id_tag, False)
            # if not member_has_step_id and Helpers.is_PW_tagged(datablock_member):
            #     logger.debug(f"'{datablock_member.name}' has no step ID")
            #     remove_thing(datablock_member, datablock_type, scene)
            #     continue

            # remove any PW tagged objects holding a step id of a step flagged for execution
            member_step_id = datablock_member[Helpers.PW_step_id_tag]
            if step_id_to_delete == member_step_id and Helpers.is_PW_tagged(datablock_member):
                
                if datablock_member != col_step:
                    remove_thing(datablock_member, datablock_type, scene)
                elif include_col:
                    remove_thing(datablock_member, datablock_type, scene)
