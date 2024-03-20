
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
import datetime
from math import degrees
from mathutils import Matrix, Vector, Color
import numpy as np
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, FloatProperty


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
            f.write("intrinsic_data\n")
            f.write(str(intrinsic_data))
            f.write("extrinsic_data\n")
            for m in extrinsic_data:
                f.write(str(m))
                f.write("\n")
            
def get_intrinsic_matrix(scene, camera):
    intrinsic_matrixes = []
    for frame_num in range(scene.frame_start, scene.frame_end):
        scene.frame_set(frame_num)
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
        K = np.array([[f_x, 0, c_x], [0, f_y, c_y], [0,   0,   1]]).astype('float32')
        intrinsic_matrixes.append(K)
        
    return intrinsic_matrixes

def get_extrinsic_matrix(scene, camera):
    ## TODO: check blender xyz and openGL xyz (https://stackoverflow.com/questions/64977993/applying-opencv-pose-estimation-to-blender-camera)
    extrinsic_matrixes = []
    for frame_num in range(scene.frame_start, scene.frame_end):
            scene.frame_set(frame_num)
            cam_matrix = np.array([v for v in camera.matrix_basis]).reshape(4,4).astype('float32')
            extrinsic_matrixes.append(cam_matrix)
            
    return extrinsic_matrixes
            
def get_cam_data(context):
    scene = context.scene
    
    if context.scene.camera is None:
        raise AssertionError("Cannot find camera")
    else:
        camera = context.scene.camera
        intrinsic_matrixes = get_intrinsic_matrix(scene, camera)
        extrinsic_matrixes = get_extrinsic_matrix(scene, camera)
            
        return extrinsic_matrixes, intrinsic_matrixes


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