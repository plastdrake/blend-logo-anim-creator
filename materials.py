"""MaterialFactory (GRASP Creator + Factory).

Single place that builds every shader. Materials are cached by name so repeated
builds reuse instead of duplicating node trees (DRY, reusability).
"""
import bpy


def set_socket(sock, value):
    """Assign a node-socket default, tolerating 3- vs 4-channel colors."""
    try:
        if sock is None:
            return
        dv = sock.default_value
        if hasattr(dv, "__len__") and not isinstance(value, (int, float)):
            want = len(dv)
            v = tuple(value)
            if len(v) == 3 and want == 4:
                v = (v[0], v[1], v[2], 1.0)
            elif len(v) == 4 and want == 3:
                v = v[:3]
            sock.default_value = v
        else:
            sock.default_value = value
    except Exception:
        try:
            sock.default_value = value
        except Exception:
            pass


class MaterialFactory:
    def __init__(self):
        self._cache = {}

    # -- generic builders -------------------------------------------------
    def principled(self, name, base=(0.85, 0.88, 1.0, 1.0), metallic=0.85,
                   roughness=0.22, emission=(0.2, 0.55, 1.0, 1.0),
                   emission_strength=0.6):
        if name in self._cache:
            return self._cache[name]
        mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        mat.use_nodes = True
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        nodes.clear()
        out = nodes.new("ShaderNodeOutputMaterial")
        out.location = (300, 0)
        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.location = (0, 0)
        set_socket(bsdf.inputs.get("Base Color"), base)
        set_socket(bsdf.inputs.get("Metallic"), metallic)
        set_socket(bsdf.inputs.get("Roughness"), roughness)
        set_socket(bsdf.inputs.get("Emission Color"), emission)
        if bsdf.inputs.get("Emission Strength"):
            set_socket(bsdf.inputs.get("Emission Strength"), emission_strength)
        elif bsdf.inputs.get("Emission"):
            set_socket(bsdf.inputs.get("Emission"), emission)
        links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
        self._cache[name] = mat
        return mat

    def emission(self, name, color=(1.0, 0.45, 0.05, 1.0), strength=3.0):
        """Pure glow material (unlit: fast, no lamps needed)."""
        if name in self._cache:
            return self._cache[name]
        mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        mat.use_nodes = True
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        nodes.clear()
        out = nodes.new("ShaderNodeOutputMaterial")
        emis = nodes.new("ShaderNodeEmission")
        emis.name = "Emission"
        set_socket(emis.inputs.get("Color"), color)
        set_socket(emis.inputs.get("Strength"), strength)
        links.new(emis.outputs["Emission"], out.inputs["Surface"])
        self._cache[name] = mat
        return mat

    def transparent(self, name):
        """Invisible mesh (emitter shells that must not occlude)."""
        if name in self._cache:
            return self._cache[name]
        mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        mat.use_nodes = True
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        nodes.clear()
        out = nodes.new("ShaderNodeOutputMaterial")
        transp = nodes.new("ShaderNodeBsdfTransparent")
        links.new(transp.outputs["BSDF"], out.inputs["Surface"])
        self._cache[name] = mat
        return mat

    def volume(self, name, color=(0.35, 0.55, 1.0, 1.0), density=0.02):
        if name in self._cache:
            return self._cache[name]
        mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        mat.use_nodes = True
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        nodes.clear()
        out = nodes.new("ShaderNodeOutputMaterial")
        pv = nodes.new("ShaderNodeVolumePrincipled")
        try:
            pv.inputs["Density"].default_value = density
            pv.inputs["Anisotropy"].default_value = 0.4
            set_socket(pv.inputs.get("Color"), color)
        except Exception:
            pass
        links.new(pv.outputs["Volume"], out.inputs["Volume"])
        self._cache[name] = mat
        return mat

    def smoke_card(self, name, color=(0.35, 0.6, 1.0, 1.0), strength=0.12):
        """Cheap animated smoke: noise-driven emission, W animated by #frame."""
        if name in self._cache:
            return self._cache[name]
        mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        mat.use_nodes = True
        mat.blend_method = "BLEND"
        try:
            mat.show_transparent_back = False
        except Exception:
            pass
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        nodes.clear()
        out = nodes.new("ShaderNodeOutputMaterial")
        transp = nodes.new("ShaderNodeBsdfTransparent")
        emis = nodes.new("ShaderNodeEmission")
        set_socket(emis.inputs.get("Color"), color)
        try:
            emis.inputs["Strength"].default_value = strength
        except Exception:
            pass
        tex = nodes.new("ShaderNodeTexNoise")
        try:
            tex.inputs["Scale"].default_value = 2.2
            tex.inputs["Detail"].default_value = 4.0
        except Exception:
            pass
        try:  # drift the noise with the timeline
            drv = tex.inputs["W"].driver_add("default_value").driver
            drv.type = "SCRIPTED"
            v = drv.variables.new()
            v.name = "frame"
            v.type = "SINGLE_PROP"
            tgt = v.targets[0]
            tgt.id_type = "SCENE"
            tgt.id = bpy.context.scene
            tgt.data_path = "frame_current"
            drv.expression = "frame*0.08"
        except Exception:
            pass
        ramp = nodes.new("ShaderNodeValToRGB")
        try:
            ramp.color_ramp.elements[0].position = 0.55
            ramp.color_ramp.elements[1].position = 0.95
        except Exception:
            pass
        mix = nodes.new("ShaderNodeMixShader")
        try:
            mix.inputs["Fac"].default_value = 0.5
        except Exception:
            pass
        links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"], mix.inputs["Fac"])
        links.new(transp.outputs["BSDF"], mix.inputs[1])
        links.new(emis.outputs["Emission"], mix.inputs[2])
        links.new(mix.outputs["Shader"], out.inputs["Surface"])
        self._cache[name] = mat
        return mat

    def trail(self, name, color=(1.0, 0.45, 0.05, 1.0), strength=4.0):
        """Light-trail material with a keyframable 'Reveal' (0 = invisible)."""
        mat = self.emission(name + "_Glow", color, strength)
        # rebuild as mix so reveal can fade it; keep node names stable
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        nodes.clear()
        out = nodes.new("ShaderNodeOutputMaterial")
        transp = nodes.new("ShaderNodeBsdfTransparent")
        emis = nodes.new("ShaderNodeEmission")
        emis.name = "Emission"
        set_socket(emis.inputs.get("Color"), color)
        set_socket(emis.inputs.get("Strength"), strength)
        mix = nodes.new("ShaderNodeMixShader")
        mix.name = "Reveal"
        try:
            mix.inputs["Fac"].default_value = 1.0
        except Exception:
            pass
        links.new(transp.outputs["BSDF"], mix.inputs[1])
        links.new(emis.outputs["Emission"], mix.inputs[2])
        links.new(mix.outputs["Shader"], out.inputs["Surface"])
        self._cache[name] = mat
        return mat

    @staticmethod
    def flash(mat, frame, peak, base=3.0, width=8):
        """Emission spike around `frame` (garnish; failures are swallowed)."""
        try:
            emis = mat.node_tree.nodes.get("Emission")
            sock = emis.inputs["Strength"]
            for f, v in ((frame - width, base), (frame, peak), (frame + width, base)):
                sock.default_value = v
                sock.keyframe_insert(data_path="default_value", frame=f)
        except Exception:
            pass
