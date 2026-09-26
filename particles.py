"""Small helpers shared by particle-based effects."""
from .animation import Animator


def fade_prototypes(prototypes, f0, f1):
    """Scale spark prototypes 1 -> 0 so every instance fades out together.

    Scaling the prototype (rather than the emitter) is what makes the whole
    multi-colour particle field disappear in sync.
    """
    for proto in prototypes:
        proto.scale = (1.0,) * 3
        proto.keyframe_insert(data_path="scale", frame=f0)
        proto.scale = (0.0,) * 3
        proto.keyframe_insert(data_path="scale", frame=f1)
        Animator.ease(proto, "scale", "SINE", "IN")
        try:
            proto.hide_render = False  # hiding it would hide its instances
        except Exception:
            pass
    return prototypes
