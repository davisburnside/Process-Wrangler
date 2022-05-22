import bpy 
from bpy.app.handlers import persistent

@persistent
def pw_text_datablock_change_handler(scene):
    
    try:
        idxs_to_delete = []

        for process in scene.processwrangler_data.scene_processes:

            for index, step in enumerate(process.steps_list):
                if not step.step_script:
                    idxs_to_delete.append(index)
            for idx in idxs_to_delete:
                process.steps_list.remove(idx)
    except:
        print("? error in text_datablock_change_handler")
    
def register():
    
#    bpy.app.handlers.depsgraph_update_pre.clear() # for testing
    
    add_listener = True
    for handler in bpy.app.handlers.depsgraph_update_pre:
        if handler.__name__ == "text_datablock_change_handler":
            add_listener = False
            break
    if add_listener:
        print("add Handler to bpy.app.handlers.depsgraph_update_pre")
        bpy.app.handlers.depsgraph_update_pre.append(pw_text_datablock_change_handler)

def unregister():
    
    try:
        bpy.app.handlers.frame_change_post.remove(pw_text_datablock_change_handler)
    except:
        print("Unable to remove 'text_datablock_change_handler' from bpy.app.handlers.frame_change_post")
    pass