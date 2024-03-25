
bl_info = {
    "name": "Export: Rendering Data",
    "description": "Export Cameras",
    "author": "Jiyun Won",
    "location": "File > Export > Rendering Data",
    "warning": "",
    "category": "Import-Export",
}

import bpy
import os
import numpy as np
from bpy_extras.io_utils import ExportHelper

def get_intrinsic_matrix(scene, camera):        
        # scene.frame_set(frame_num)
        cam_data = camera.data
        f_in_mm = cam_data.lens
        sensor_width_in_mm = cam_data.sensor_width
        w = scene.render.resolution_x
        h = scene.render.resolution_y
        pixel_aspect = scene.render.pixel_aspect_y / scene.render.pixel_aspect_x
        f_x = f_in_mm / sensor_width_in_mm * w
        f_y = f_x * pixel_aspect
        c_x = w * (0.5 - cam_data.shift_x)
        c_y = h * 0.5 + w * cam_data.shift_y
        return np.array([[f_x, 0, c_x], [0, f_y, c_y], [0,   0,   1]]).astype('float32')    

## TODO: check blender xyz and openGL xyz (https://stackoverflow.com/questions/64977993/applying-opencv-pose-estimation-to-blender-camera)
def get_extrinsic_matrix(camera):
    return np.array([v for v in camera.matrix_basis]).reshape(4,4).astype('float32')
            
def save_cam_data(context, path):
    scene = context.scene
    if context.scene.camera is None:
        raise AssertionError("Cannot find camera")
    else:
        camera = context.scene.camera
        # intrinsic_matrixes = []
        # extrinsic_matrixes = []
        if not os.path.exists(f"{path}camera"):
            os.makedirs(f"{path}camera")
            os.makedirs(f"{path}camera\\intrinsic")
            os.makedirs(f"{path}camera\\extrinsic")
            
        for frame_num in range(scene.frame_start, scene.frame_end):
            scene.frame_set(frame_num)
            np.save(f"{path}camera\\intrinsic\\{frame_num:03d}", get_intrinsic_matrix(scene, camera))
            np.save(f"{path}camera\\extrinsic\\{frame_num:03d}", get_extrinsic_matrix(camera))
        # return extrinsic_matrixes, intrinsic_matrixes

def save_render_img(context, forder_path):
    context.scene.use_nodes = True
    context.view_layer.use_pass_z = True
    tree = context.scene.node_tree
    links = tree.links
    # clear default nodes
    for n in tree.nodes:
        tree.nodes.remove(n)
    # create input render layer node
    rl = tree.nodes.new('CompositorNodeRLayers')
    normalize = tree.nodes.new(type='CompositorNodeNormalize')
    links.new(rl.outputs[2], normalize.inputs[0])

    invert = tree.nodes.new(type="CompositorNodeInvert")
    links.new(normalize.outputs[0], invert.inputs[1])
    
    depthViewer = tree.nodes.new(type="CompositorNodeViewer")
    links.new(invert.outputs[0], depthViewer.inputs[0])

    links.new(rl.outputs[1], depthViewer.inputs[1])
    output = tree.nodes.new(type="CompositorNodeOutputFile")
    # ('BMP', 'IRIS', 'PNG', 'JPEG', 'JPEG2000', 'TARGA', 'TARGA_RAW', 'CINEON', 'DPX', 'OPEN_EXR_MULTILAYER', 'OPEN_EXR', 'HDR', 'TIFF', 'WEBP')
    output.format.file_format = "JPEG"
    output.format.color_depth = "8" 
    output.base_path = f"{forder_path}\\depth_img"

    links.new(invert.outputs[0], output.inputs[0])

    context.scene.render.image_settings.file_format='JPEG'
    
    w = context.scene.render.resolution_x
    h = context.scene.render.resolution_y
    
    if not os.path.exists(f"{forder_path}depth"):
        os.makedirs(f"{forder_path}depth")
        
    for frame_num in range(context.scene.frame_start, context.scene.frame_end):
        context.scene.frame_set(frame_num)
        context.scene.render.filepath = f"{forder_path}\\rgb\\{frame_num:03d}.jpg"
        bpy.ops.render.render(False, animation=False, write_still=True)
        pixels = np.array(bpy.data.images['Viewer Node'].pixels).reshape(h,w,4)
        pixels = (pixels.transpose()[0]).transpose()
        pixels = np.flip(pixels, 0)
        np.save(f"{forder_path}depth\\{frame_num:03d}", pixels.astype(np.float32))

######
class ExportData(bpy.types.Operator, ExportHelper):
    """Export selected cameras and objects animation to After Effects"""
    bl_idname = "export.jpg"
    bl_label = "Rendering images & save cameras"
    bl_options = {'PRESET', 'UNDO'}
    filename_ext = ".jpg"

    @classmethod
    def poll(cls, context):
        selected = context.selected_objects
        camera = context.scene.camera
        return selected or camera

    def execute(self, context):
        path = self.filepath.split('.')[0]
        name_len = len(path.split('\\')[-1])
        forder_path = path[:-name_len]
        save_cam_data(context, forder_path)
        save_render_img(context, forder_path)
        print("\nExport data Completed")
        return {'FINISHED'}


def menu_func(self, context):
    self.layout.operator(
        ExportData.bl_idname, text="Export Rendering Data")

def register():
    bpy.utils.register_class(ExportData)
    bpy.types.TOPBAR_MT_file_export.append(menu_func)
    

def unregister():
    bpy.utils.unregister_class(ExportData)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func)

register()