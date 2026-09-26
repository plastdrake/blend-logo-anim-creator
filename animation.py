"""Animator: keyframing helpers shared by the styles.

High cohesion: nothing here touches materials, geometry or the scene - only
object transforms, shape-key values and easing.
"""
import math


class Animator:
    @staticmethod
    def fcurves(action):
        """Version-proof f-curve access (4.x legacy vs 5.x layered actions)."""
        try:
            return list(action.fcurves)
        except (AttributeError, TypeError):
            pass
        out = []
        try:
            for layer in action.layers:
                for strip in layer.strips:
                    try:
                        bags = list(strip.channelbags)
                    except Exception:
                        continue
                    for bag in bags:
                        try:
                            out.extend(list(bag.fcurves))
                        except Exception:
                            pass
        except Exception:
            pass
        return out

    @staticmethod
    def _action(obj):
        ad = getattr(obj, "animation_data", None)
        return ad.action if ad and ad.action else None

    @staticmethod
    def pose(obj, frame):
        """Keyframe location + rotation + scale."""
        obj.keyframe_insert(data_path="location", frame=frame)
        obj.keyframe_insert(data_path="rotation_euler", frame=frame)
        obj.keyframe_insert(data_path="scale", frame=frame)

    @staticmethod
    def ease(obj, data_path, interpolation, easing="OUT"):
        Animator.ease_owner(obj, data_path, interpolation, easing)

    @staticmethod
    def ease_owner(owner, data_path, interpolation, easing="OUT"):
        """Ease f-curves on any animated datablock (objects, shape keys...)."""
        action = Animator._action(owner)
        if action is None:
            return
        for fc in Animator.fcurves(action):
            if fc.data_path != data_path:
                continue
            for kp in fc.keyframe_points:
                kp.interpolation = interpolation
                try:
                    kp.easing = easing
                except Exception:
                    pass

    @staticmethod
    def set_key_interpolation(obj, data_path, frame, interpolation,
                              easing="AUTO"):
        """Set interpolation on the keyframe at `frame` (governs its segment)."""
        action = Animator._action(obj)
        if action is None:
            return
        for fc in Animator.fcurves(action):
            if fc.data_path != data_path:
                continue
            for kp in fc.keyframe_points:
                if abs(kp.co.x - frame) < 0.5:
                    kp.interpolation = interpolation
                    try:
                        kp.easing = easing
                    except Exception:
                        pass

    @staticmethod
    def grow_from(obj, f_start, f_end, start_location, end_location,
                  base_rotation, start_scale=0.06, spin=0.32, arc=0.0):
        """Grow an object out of a point and settle it into its slot.

        Keeps `base_rotation` throughout (plus a small z-swivel that relaxes to
        zero) so the result never reads as flipped or mirrored, and stays
        invisible until its beat starts.
        """
        start_rot = (base_rotation[0], base_rotation[1],
                     base_rotation[2] + spin)
        # hidden until the beat (CONSTANT holds the tiny scale in place)
        obj.location = start_location
        obj.rotation_euler = start_rot
        obj.scale = (0.001,) * 3
        for dp in ("location", "rotation_euler", "scale"):
            obj.keyframe_insert(data_path=dp, frame=1)
            Animator.set_key_interpolation(obj, dp, 1, "CONSTANT", "AUTO")
        # sprout
        obj.location = start_location
        obj.rotation_euler = start_rot
        obj.scale = (start_scale,) * 3
        for dp in ("location", "rotation_euler", "scale"):
            obj.keyframe_insert(data_path=dp, frame=f_start)
        # optional lifted flight path
        if arc:
            mid = int((f_start + f_end) / 2)
            obj.location = ((start_location[0] + end_location[0]) / 2.0,
                            start_location[1],
                            (start_location[2] + end_location[2]) / 2.0 + arc)
            obj.keyframe_insert(data_path="location", frame=mid)
            Animator.set_key_interpolation(obj, "location", mid, "SINE")
        # settle
        obj.location = end_location
        obj.rotation_euler = base_rotation
        obj.scale = (1.0, 1.0, 1.0)
        for dp in ("location", "rotation_euler", "scale"):
            obj.keyframe_insert(data_path=dp, frame=f_end)
        Animator.set_key_interpolation(obj, "location", f_start, "SINE", "OUT")
        Animator.set_key_interpolation(obj, "rotation_euler", f_start,
                                       "SINE", "OUT")
        Animator.set_key_interpolation(obj, "scale", f_start, "BACK", "OUT")
        return obj

    @staticmethod
    def pop(obj, f_hit, base_scale, amount=1.12, settle_frame=None):
        """Quick overshoot on scale (impact pop)."""
        obj.scale = tuple(s * amount for s in base_scale)
        obj.keyframe_insert(data_path="scale", frame=f_hit)
        if settle_frame:
            obj.scale = base_scale
            obj.keyframe_insert(data_path="scale", frame=settle_frame)
            Animator.ease(obj, "scale", "ELASTIC")
