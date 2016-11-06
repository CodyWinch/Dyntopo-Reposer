#====================== BEGIN GPL LICENSE BLOCK ======================
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
#======================= END GPL LICENSE BLOCK ========================

# <pep8 compliant>

bl_info = {
    "name": "Dyntopo Reposer",
    "version": (1, 0),
    "author": "Cody Winchester (codywinch)",
    "blender": (2, 78, 0),
    "description": "Reposing dynamic topology sculpts",
    "location": "Sculpt tab of the Tool Shelf",
    "category": "Sculpting"}

import bpy
import math
import mathutils
from bpy.props import *

class DyntopoReposerPanel(bpy.types.Panel):
    """Creates a Panel in the scene context of the properties editor"""
    bl_category = 'Sculpt'
    bl_label = "Dyntopo Reposer"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'

    
    @classmethod
    def poll(cls, context):
        aobj = context.active_object
        return aobj is not None and aobj.type == 'MESH'
    
    #Creates the properties under the toolbar
    object = bpy.types.Object
    
    object.RP_decimate_percent = FloatProperty(name = "Decimation Percenetage", description = "Decimation percentage", default = 0.1, min = 0, max = 100)
    object.RP_seperation_dist = IntProperty(name = "Seperation Distance", description = "Distance in blender units between sculpt and reposing objects", default = 25, min = 0, max = 100)
    object.RP_quality_levels = IntProperty(name = "Quality Level", description = "Quality level of the reposing higher quality the longer it will take", default = 3, min = 0, max = 6)
    object.RP_pose_ob = StringProperty(name = "Posed Object", maxlen=1024)
    object.RP_limit_selected = BoolProperty(name = "Selected Vertices Only (Speedup)", description = 'Only repose selected vertices, This can speed up the operation', default = True)

    def draw(self, context):
        layout = self.layout
        aobj = context.active_object
        sce = context.scene
        me = aobj.data
        
        row = layout.row()
        row.alignment = 'CENTER'
        row.scale_y = 1.5
        row.label(text = "CREATE REPOSER OBJECTS")
        
        row = layout.row()
        row.alignment = 'CENTER'
        row.prop(aobj, "RP_seperation_dist")
        
        row = layout.row()
        row.alignment = 'CENTER'
        row.prop(aobj, "RP_decimate_percent")
        
        row = layout.row()
        row.alignment = 'CENTER'
        row.scale_y = 1.5
        row.operator("object.create_lowres_poser")
        
        row = layout.row()
        row.alignment = 'CENTER'
        row.scale_y = 1.5
        row.label(text = "REPOSE SCULPT")
            
        row = layout.row()
        row.prop_search(aobj, "RP_pose_ob", context.scene, "objects", text="Posed Sculpt Object")
        
        row = layout.row()
        row.alignment = 'CENTER'
        row.prop(aobj, "RP_limit_selected")
        
        row = layout.row()
        row.alignment = 'CENTER'
        row.prop(aobj, "RP_quality_levels")
        
        row = layout.row()
        row.alignment = 'CENTER'
        row.scale_y = 2.5
        row.operator("object.repose_sculpt")
        
        if aobj.RP_pose_ob == '':
            row.enabled = False

class CreatePoserModel(bpy.types.Operator):
    bl_idname = "object.create_lowres_poser"
    bl_label = "Create Poser Model"
    
    def execute(self, context):
        data = bpy.data
        context = bpy.context
        scn = context.scene
        aobj = context.active_object
        
        poser_name = 'RP_Posed Object'
        
        bpy.ops.object.duplicate_move(TRANSFORM_OT_translate={"value":(aobj.RP_seperation_dist,0,0), "constraint_axis":(True,False,False)})
        
        context.active_object.modifiers.new('Decimate', 'DECIMATE')
        context.active_object.modifiers[0].ratio = aobj.RP_decimate_percent
        context.active_object.name = poser_name
        pose_object = context.active_object.name
        bpy.ops.object.convert(target='MESH')
        
        context.active_object.shape_key_add(name='Base', from_mix=True)
        context.active_object.shape_key_add(name='Pose', from_mix=True)
        context.active_object.active_shape_key_index = 1
        context.active_object.data.shape_keys.key_blocks[1].value = 1.0
        
        aobj.RP_pose_ob = pose_object
        return {'FINISHED'}
    
class ReposeSculpt(bpy.types.Operator):
    bl_idname = "object.repose_sculpt"
    bl_label = "Repose Sculpt"
    
    def execute(self, context):
        data = bpy.data
        context = bpy.context
        scn = context.scene
        aobj = context.active_object
        spacing = aobj.RP_seperation_dist 
        target = data.objects[aobj.RP_pose_ob]
        
        aobj.select = False
        target.select = True
        scn.objects.active = target
        
        if aobj.data.shape_keys == None:
            pose_name = 'REPOSE SHAPE 1'
            
            aobj.shape_key_add(name='Basis', from_mix=True)
            aobj.shape_key_add(name=pose_name, from_mix=True)
            aobj.active_shape_key_index = 1
        else:
            count = 1
            index = 0
            for kb in aobj.data.shape_keys.key_blocks:
                if kb.name.startswith('REPOSE SHAPE '):
                    count += 1
                    index += 1
            pose_name = 'REPOSE SHAPE ' + str(count)
            aobj.shape_key_add(name=pose_name, from_mix=True)
            aobj.active_shape_key_index = index
        
        aobj.data.shape_keys.key_blocks[pose_name].value = 1.0
        
        bpy.ops.object.subdivision_set(level=aobj.RP_quality_levels)
        
        skeys = []
        for kb in target.data.shape_keys.key_blocks:
            skeys.append(kb.mute)
        
        posed_dat = target.to_mesh(scene = scn, apply_modifiers = True, settings = ('PREVIEW'))
        
        for kb in target.data.shape_keys.key_blocks:
            kb.mute = True
        neutral_dat = target.to_mesh(scene = scn, apply_modifiers = True, settings = ('PREVIEW'))
        i = 0
        for kb in target.data.shape_keys.key_blocks:
            kb.mute = skeys[i]
            i += 1
        
        for mod in target.modifiers:
            target.modifiers.remove(mod)
        
        aobj.select = True
        target.select = False
        scn.objects.active = aobj
        
        mesh = neutral_dat
        size = len(mesh.vertices)
        kd = mathutils.kdtree.KDTree(size)
        
        for i, v in enumerate(mesh.vertices):
            kd.insert(v.co, i)
        
        kd.balance()
        
        if aobj.RP_limit_selected:
            for vert in aobj.data.vertices:
                if vert.select:
                    near_bys = []
                    for (co, index, dist) in kd.find_n(vert.co, 3):
                        near_bys.append(index)
                    avg_vec = mathutils.Vector((0.0, 0.0, 0.0))
                    for ind in near_bys:
                        vec = posed_dat.vertices[ind].co - neutral_dat.vertices[ind].co
                        avg_vec += vec
                        
                    avg_vec = avg_vec / 3
                    
                    aobj.data.shape_keys.key_blocks[pose_name].data[vert.index].co += avg_vec
        else:
            for vert in aobj.data.vertices:
                near_bys = []
                for (co, index, dist) in kd.find_n(vert.co, 3):
                    near_bys.append(index)
                avg_vec = mathutils.Vector((0.0, 0.0, 0.0))
                for ind in near_bys:
                    vec = posed_dat.vertices[ind].co - neutral_dat.vertices[ind].co
                    avg_vec += vec
                    
                avg_vec = avg_vec / 3
                
                aobj.data.shape_keys.key_blocks[pose_name].data[vert.index].co += avg_vec

        data.meshes.remove(neutral_dat)
        data.meshes.remove(posed_dat)
        return {'FINISHED'}
    


def register():
    bpy.utils.register_class(DyntopoReposerPanel)
    bpy.utils.register_class(CreatePoserModel)
    bpy.utils.register_class(ReposeSculpt)

def unregister():
    bpy.utils.unregister_class(DyntopoReposerPanel)
    bpy.utils.unregister_class(CreatePoserModel)
    bpy.utils.unregister_class(ReposeSculpt)
    
if __name__ == "__main__":
    register()