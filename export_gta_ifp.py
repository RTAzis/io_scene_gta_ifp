import bpy

from mathutils import Vector, Quaternion
from . ifp import Ifp, Bone, Keyframe, ANIM_CLASSES


def invalid_active_object(self, context):
    self.layout.label(text='You need to select the armature to export animation')


def is_bone_taged(bone):
    return bone.get('bone_id') is not None


def get_pose_data(arm_obj, act):
    all_bones = [bone for bone in arm_obj.data.bones if is_bone_taged(bone)]
    pose_data = {}

    for curve in act.fcurves:
        if 'pose.bones' not in curve.data_path:
            continue

        bone_name = curve.data_path.split('"')[1]
        bone = arm_obj.data.bones.get(bone_name)
        if bone not in all_bones:
            continue

        if bone not in pose_data:
            pose_data[bone] = {'kfs': {}, 'type': 3}

        for kp in curve.keyframe_points:
            time = int(kp.co[0])
            if time not in pose_data[bone]['kfs']:
                pose_data[bone]['kfs'][time] = (Vector(), Quaternion())

            if curve.data_path == 'pose.bones["%s"].location' % bone_name:
                pose_data[bone]['kfs'][time][0][curve.array_index] = kp.co[1]
                pose_data[bone]['type'] = 4
            elif curve.data_path == 'pose.bones["%s"].rotation_quaternion' % bone_name:
                pose_data[bone]['kfs'][time][1][curve.array_index] = kp.co[1]

    return pose_data


def create_ifp_animations(arm_obj, anim_cls, actions):
    animations = []

    for act in actions:
        anim = anim_cls(act.name, [])

        pose_mats = get_pose_data(arm_obj, act)
        for bone, data in pose_mats.items():

            keyframes = []
            for time, tr in data['kfs'].items():
                loc, rot = tr

                loc_mat = bone.matrix_local.copy()
                if bone.parent:
                    loc_mat = bone.parent.matrix_local.inverted_safe() @ loc_mat

                kf = Keyframe(time, loc + loc_mat.to_translation(), (loc_mat @ rot.to_matrix().to_4x4()).to_quaternion())
                keyframes.append(kf)

            anim.bones.append(Bone(bone.name, data['type'], bone['bone_id'], keyframes))

        animations.append(anim)
    return animations


def save(context, filepath, name, version):
    arm_obj = context.view_layer.objects.active
    if not arm_obj or type(arm_obj.data) != bpy.types.Armature:
        context.window_manager.popup_menu(invalid_active_object, title='Error', icon='ERROR')
        return {'CANCELLED'}

    animations = create_ifp_animations(arm_obj, ANIM_CLASSES[version], bpy.data.actions)

    ifp = Ifp(name, version, animations)
    ifp.save(filepath)

    return {'FINISHED'}
