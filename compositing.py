"""Glow compositing (Single Responsibility; version Polymorphism inside).

Blender 4.x uses scene.node_tree with glare *properties*; Blender 5.x uses
scene.compositing_node_group where the glare settings are *input sockets*.
Both are handled here, including the 5.x socket names ("Fog Glow", "High").
"""
import bpy

#: socket values per Blender version family
_QUALITIES = ("High", "Medium", "Low")


def _get_tree(scene):
    try:  # 4.x path
        if hasattr(scene, "node_tree"):
            try:
                scene.use_nodes = True
            except Exception:
                pass
            if scene.node_tree is not None:
                return scene.node_tree, "LEGACY"
    except Exception:
        pass
    try:  # 5.x path
        tree = scene.compositing_node_group
        if tree is None:
            tree = bpy.data.node_groups.new(name="LogoAnim Compositing",
                                            type="CompositorNodeTree")
            scene.compositing_node_group = tree
        return tree, "GROUP"
    except Exception:
        pass
    return None, "NONE"


def _set_socket(node, name, value):
    sock = node.inputs.get(name)
    if sock is None:
        return False
    try:
        sock.default_value = value
        return True
    except Exception:
        return False


def _set_prop(node, name, value):
    try:
        setattr(node, name, value)
        return getattr(node, name, None) == value
    except Exception:
        return False


def configure_glare(node, glare_type="Fog Glow", threshold=0.5, strength=1.4,
                    size=8.0, saturation=1.2, smoothness=0.5):
    """Configure a Glare node whatever API flavour it exposes."""
    ok = False
    for name in (glare_type, glare_type.upper().replace(" ", "_")):
        if _set_socket(node, "Type", name) or _set_prop(node, "glare_type", name):
            ok = True
            break
    for value in _QUALITIES:
        if _set_socket(node, "Quality", value) or _set_prop(node, "quality", value):
            break
    for sock, prop, value in (("Threshold", "threshold", threshold),
                              ("Strength", "mix", strength),
                              ("Size", "size", size),
                              ("Saturation", "saturation", saturation),
                              ("Smoothness", "smoothness", smoothness)):
        _set_socket(node, sock, value) or _set_prop(node, prop, value)
    return ok


def setup_glow(intensity=1.0):
    """Two chained glare passes: a tight fog glow plus a wide bloom."""
    scene = bpy.context.scene
    tree, kind = _get_tree(scene)
    if tree is None:
        return
    nodes, links = tree.nodes, tree.links
    nodes.clear()
    rl = nodes.new("CompositorNodeRLayers")
    rl.location = (-500, 0)
    tight = nodes.new("CompositorNodeGlare")
    tight.location = (-200, 0)
    wide = nodes.new("CompositorNodeGlare")
    wide.location = (100, 0)
    configure_glare(tight, "Fog Glow", threshold=0.92,
                    strength=0.42 * intensity, size=6.0, saturation=1.20,
                    smoothness=0.45)
    configure_glare(wide, "Bloom", threshold=1.0,
                    strength=0.28 * intensity, size=8.0, saturation=1.10,
                    smoothness=0.6)
    if kind == "LEGACY":
        out = nodes.new("CompositorNodeComposite")
        out.location = (400, 0)
        dst = out.inputs["Image"]
    else:
        try:
            tree.interface.new_socket(name="Image", in_out="OUTPUT",
                                      socket_type="NodeSocketColor")
        except Exception:
            pass
        out = nodes.new("NodeGroupOutput")
        out.location = (400, 0)
        try:
            dst = out.inputs.get("Image") or out.inputs[0]
        except Exception:
            return
    links.new(rl.outputs["Image"], tight.inputs["Image"])
    links.new(tight.outputs["Image"], wide.inputs["Image"])
    links.new(wide.outputs["Image"], dst)
