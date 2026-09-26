# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed
- Relicensed to **MIT** — free for anyone to use, modify and share, including
  commercially.

## [1.2.0] - 2026-09-27

### Added
- **Font picker**: a Font dropdown listing installed system fonts, plus a
  Custom font file field for any `.ttf`/`.otf`.
- **Brightness** (global exposure multiplier) and **Glow** (bloom strength)
  controls.
- **Settle hold** (seconds of finished logo at the end); beats are now fractions
  of an action window, so the pacing holds at any duration.
- Branching plant: the cord grows branches that arc outward, each carrying a
  leaf that opens while the branch is still growing (speedlapse timing).
- Leaf **unroll** via a `Furled` shape key — leaves open from a coiled shoot
  instead of just scaling up.
- Multi-coloured, much smaller particle palette.
- Invisible **sweeping light** that lights the metal as it passes and switches
  off afterwards.
- Metallic materials for the plug, the second word and the plant, lit by a
  dedicated area-light rig with Eevee raytracing.
- `tools/check_manifest.py` (Blender-free manifest validation) and a GitHub
  Actions workflow.

### Changed
- **Architecture rewrite** from a single module into focused modules
  (config, materials, scene_setup, text_logo, icons, plug, plant, curves,
  animation, fx, particles, compositing, output, styles, director, UI).
- Glow is now two chained glare passes and is configured through Blender 5's
  glare **input sockets** — previously the settings silently failed and no glow
  was rendered at all.
- Default frame count 120 → 300, with a 2 s settle hold.
- Overall brightness reduced and made configurable.

### Fixed
- Installed extension was missing every module except `__init__.py`; the
  deployer now ships and verifies the complete package.
- Particles never rendered in Eevee (one unsupported property aborted the rest
  of the particle setup, leaving the halo render type).
- Spiral/arc helpers built geometry in the XY plane, so curves rendered
  edge-on as flat lines.
- Particle emitters were flat planes seen edge-on, collapsing bursts into
  visible straight lines.
- Long company names overflowed the frame and collided with the icon; text is
  measured, fitted and the camera frames the content.
- Cord joined the plug with a visible lip and a right-angled elbow.
- Branch tips poked out past the leaf bases.

## [1.1.0] - 2026-09-26

### Added
- `PLUG` style: a 3.5 mm jack flies in, a cord grows from it and the company
  name grows out of the plant.
- Draft render (50% resolution, heavy FX hidden, settings restored afterwards).
- Python deployment tooling: `tools/deploy.py`, headless smoke tests, install
  verification.
- Font/dataset-level polish: glow compositing, light shafts, dust.

### Changed
- Replaced the PowerShell deploy script with a Python one.

## [1.0.0] - 2026-09-26

### Added
- Initial release: `STUDIO` style (extruded text + procedural icon fly-in),
  expressive easing, camera dolly, volumetric shafts, smoke cards, dust, glow,
  and one-click MP4 render.
- Five procedural icon presets: gem + rings, torus knot, shield, cube abstract,
  orbit spheres.
- Blender extension manifest and UI panel.

[Unreleased]: https://github.com/plastdrake/blend-logo-anim-creator/compare/v1.2.0...main
[1.2.0]: https://github.com/plastdrake/blend-logo-anim-creator/releases/tag/v1.2.0
[1.1.0]: https://github.com/plastdrake/blend-logo-anim-creator
[1.0.0]: https://github.com/plastdrake/blend-logo-anim-creator
