
bl_info = {
    "name": "Export: Camera Data (.txt)",
    "description": "Export Cameras",
    "author": "Jiyun Won",
    "location": "File > Export > Camera Data(.txt)",
    "warning": "",
    "category": "Import-Export",
}

import bpy
import os
# import cv2
from math import degrees
from mathutils import Matrix, Vector, Color
import numpy as np
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, FloatProperty
# from PIL import Image

def get_camera_frame_ranges(scene, start, end):
    """Get frame ranges for each marker in the timeline

    For this, start at the end of the timeline,
    iterate through each camera-bound marker in reverse,
    and get the range from this marker to the end of the previous range.
    """
    markers = sorted((m for m in scene.timeline_markers if m.camera is not None),
                     key=lambda m:m.frame, reverse=True)

    if len(markers) <= 1:
        return [[[start, end], scene.camera],]

    camera_frame_ranges = []
    current_frame = end
    for m in markers:
        if m.frame < current_frame:
            camera_frame_ranges.append([[m.frame, current_frame + 1], m.camera])
            current_frame = m.frame - 1
    camera_frame_ranges.reverse()
    camera_frame_ranges[0][0][0] = start
    return camera_frame_ranges

def write_txt_file(path, extrinsic_data, intrinsic_data):
        # import pdb; pdb.set_trace()
        with open(path, 'w+') as f:
            print(intrinsic_data)
            print(extrinsic_data)
            frame = 0
            for intr, extr in zip(intrinsic_data, extrinsic_data):
                f.write(f"frame #{frame}\n")
                f.write("intrinsic \n")
                f.write(str(intr))
                f.write("\n")
                f.write("extrinsic \n")
                f.write(str(extr))
                f.write("\n")
                frame += 1

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
def get_extrinsic_matrix(scene, camera):
    return np.array([v for v in camera.matrix_basis]).reshape(4,4).astype('float32')
            
def get_cam_data(context):
    scene = context.scene
    if context.scene.camera is None:
        raise AssertionError("Cannot find camera")
    else:
        camera = context.scene.camera
        intrinsic_matrixes = []
        extrinsic_matrixes = []
        for frame_num in range(scene.frame_start, scene.frame_end):
            scene.frame_set(frame_num)
            intrinsic_matrixes.append(get_intrinsic_matrix(scene, camera))
            extrinsic_matrixes.append(get_extrinsic_matrix(scene, camera))
        return extrinsic_matrixes, intrinsic_matrixes

def save_render_rgb_img(context, path):
    scene = context.scene
    for frame_num in range(scene.frame_start, 10):
        scene.frame_set(frame_num)
        scene.render.image_settings.file_format='JPEG'
        scene.render.filepath = f"{path}_{frame_num}_rgb.jpg"
        bpy.ops.render.render(use_viewport = True, write_still=True)
            
def save_render_depth_img(context, path):
    bpy.context.scene.use_nodes = True
    tree = bpy.context.scene.node_tree
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
    output.base_path = "C:\\Users\\yun\\Desktop"
    links.new(invert.outputs[0], output.inputs[0])
    for frame_num in range(context.scene.frame_start, context.scene.frame_end):
        context.scene.frame_set(frame_num)
        bpy.context.scene.render.filepath = f"{path}_{frame_num}_depth.jpg"
        bpy.ops.render.render(False, animation=False, write_still=True)
        z = bpy.data.images['Viewer Node']
        z.save(filepath=f"{path}_{frame_num}_depth.jpg")

        
######
class ExportTxt(bpy.types.Operator, ExportHelper):
    """Export selected cameras and objects animation to After Effects"""
    bl_idname = "export.txt"
    bl_label = "Export cameras"
    bl_options = {'PRESET', 'UNDO'}
    filename_ext = ".txt"

    @classmethod
    def poll(cls, context):
        selected = context.selected_objects
        camera = context.scene.camera
        return selected or camera

    def execute(self, context):
        extrinsic_mtx, intrinsic_mtx = get_cam_data(context)
        write_txt_file(self.filepath, extrinsic_mtx, intrinsic_mtx)
        save_render_rgb_img(context, self.filepath.split('.')[0])
        save_render_depth_img(context, self.filepath.split('.')[0])
        print("\nExport data Completed")
        return {'FINISHED'}


def menu_func(self, context):
    self.layout.operator(
        ExportTxt.bl_idname, text="Camera Data (.txt)")

def register():
    bpy.utils.register_class(ExportTxt)
    bpy.types.TOPBAR_MT_file_export.append(menu_func)
    

def unregister():
    bpy.utils.unregister_class(ExportTxt)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func)

register()