# STRAY procedural vehicle fleet

Four original Blender 4.5 assets share meter scale, Z up, and +Y forward. The graphite Hero hypercar is approximately 4.8 m long. The black-and-white Police sedan is approximately 5.1 m long. The Heli has a 10 m fuselage and a 10 m main rotor. The rigid Truck fuel tanker is approximately 9.5 m long, with twin tires on both rear axles. All geometry, lettering, and materials are procedural. See [LICENSE.txt](LICENSE.txt) for the CC0 dedication.

## Build, render, and validate

Run these commands from this directory with the portable Blender 4.5.3 executable. Run one Blender command at a time. Each command uses four threads, and the build renders previews sequentially.

```sh
# Build all four collections and save assets.blend.
./blender-4.5.3-linux-x64/blender -b -t 4 --python-exit-code 1 --python build_assets.py

# Build and render the Police, Heli, and Truck previews.
./blender-4.5.3-linux-x64/blender -b -t 4 --python-exit-code 1 --python build_assets.py -- --fleet-render

# Build all four assets, save assets.blend, and render only truck_preview.png.
./blender-4.5.3-linux-x64/blender -b -t 4 --python-exit-code 1 --python build_assets.py -- --fleet-only Truck

# Build and explicitly rerender all three Hero views.
./blender-4.5.3-linux-x64/blender -b -t 4 --python-exit-code 1 --python build_assets.py -- --render

# Render all six views in one build.
./blender-4.5.3-linux-x64/blender -b -t 4 --python-exit-code 1 --python build_assets.py -- --render --fleet-render

# Validate the saved blend and two in-memory builds of each asset.
./blender-4.5.3-linux-x64/blender -b assets.blend -t 4 --python-exit-code 1 --python validate_assets.py
```

Build-only mode also accepts `--no-render`. Fleet previews are `police_preview.png`, `heli_preview.png`, and `truck_preview.png`. They use 1280×800 and default to 16 denoised CPU Cycles samples. Set the fleet sample count with `--fleet-samples`, for example `--fleet-render --fleet-samples 32`. Hero render mode writes `hero_front_34.png`, `hero_rear_34.png`, and `hero_side.png`. Hero defaults to 1280×800 and 24 denoised CPU Cycles samples. Set Hero overrides with arguments such as `--render --resolution 1920x1200 --samples 48`. Omitting `--render` preserves the existing Hero PNGs.

`--fleet-only` accepts `Police`, `Heli`, or `Truck`. It uses the selected asset's existing preview studio and the same sample and thread defaults as `--fleet-render`.

Rebuild `assets.blend` before validating to include the helicopter skid correction and truck glazing. Validation writes `validation.json` and leaves the blend on disk intact. It checks evaluated bounds, ground contact, hierarchy, independent controls, local spin axes, repeat-build inventories, and foreign scene data preservation.

## Collection visibility and appending

`assets.blend` opens in **STRAY Studio** with **Hero** and its **Preview** collection enabled. All four vehicle roots share the ground origin. To inspect another asset, use the collection-level monitor and camera restriction toggles in the Outliner. Enable these columns using the Outliner filter menu if needed. Disable the current vehicle and its preview rig, then enable the desired vehicle and its corresponding **Preview_Police**, **Preview_Heli**, or **Preview_Truck** collection. Select the rig's camera as the active scene camera for a manual render. Each rig has its own camera, floor, and lights. Fleet rig defaults are edited in `FLEET_STUDIOS` in the build script.

For a shot file, use **File → Append → assets.blend → Collection** and select **Hero**, **Police**, **Heli**, or **Truck**. Append the vehicle collection alone and enable its viewport and render visibility as needed. Position the appended vehicle by its root. All four build functions also return their own collection when called in Blender Python and reuse it on rebuild.

## Animation interface

All controls below are empties. Wheel and rotor rotations are local Euler channels. `L/R` denotes two names ending in `_L` and `_R`, respectively.

| Asset | Object names | Animation or use |
| --- | --- | --- |
| Hero | `Hero_Root` | Vehicle placement and orientation. |
| Hero | `Hero_Body`, `Hero_Glass` | Separate coachwork and glazing controls. |
| Hero | `Hero_Headlights`, `Hero_Taillights` | Separate emissive geometry groups. |
| Hero | `Hero_Wheel_Front_L/R`, `Hero_Wheel_Rear_L/R` | Local X spin for tires, wheels, and brake rotors. Calipers stay on the body. |
| Police | `Police_Root` | Vehicle placement and orientation. |
| Police | `Police_Body`, `Police_Glass` | Independent sedan shell and opaque glazing controls. |
| Police | `Police_Headlights`, `Police_Taillights` | Independent emissive geometry groups. |
| Police | `Police_Lightbar_Red`, `Police_Lightbar_Blue` | Four emitter lenses per side. Keyframe Emission Strength on `Police_Mat_red` or `Police_Mat_blue`. Red taillights use their own material. |
| Police | `Police_Wheel_Front_L/R`, `Police_Wheel_Rear_L/R` | Local X spin for each wheel assembly. |
| Heli | `Heli_Root` | Aircraft placement and orientation. |
| Heli | `Heli_Body`, `Heli_Glass`, `Heli_Skids` | Independent shell, cockpit glazing, and landing gear groups. |
| Heli | `Heli_MainRotor` | Local Z spin for the four-blade main rotor. |
| Heli | `Heli_TailRotor` | Local X spin for the four-blade tail rotor in the YZ plane. |
| Heli | `Heli_MainBlade_1` through `Heli_MainBlade_4`, `Heli_TailBlade_1` through `Heli_TailBlade_4` | Blade assembly empties under their rotor controls. |
| Truck | `Truck_Root` | Vehicle placement and orientation. |
| Truck | `Truck_Chassis`, `Truck_Cab`, `Truck_Glass`, `Truck_Tank` | Independent running gear, cab, glazing, and fuel vessel groups. |
| Truck | `Truck_Headlights`, `Truck_Taillights` | Independent emissive geometry groups. |
| Truck | `Truck_Wheel_Front_L/R`, `Truck_Wheel_Rear1_L/R`, `Truck_Wheel_Rear2_L/R` | Local X spin. The inboard and outboard rear tires share their side's axle pivot. |

## Verified delivery

Actual Blender 4.5.3 runtime build and renders passed. 376/376 validation checks passed; see `validation.json`, `validation.log`, and `delivery_report.txt`. Fleet previews use 16 denoised CPU samples, four threads maximum, rendered sequentially. `fleet_contact_sheet.jpg` and `fleet_night_contact_sheet.jpg` combine actual renders. Original three Hero previews are byte-for-byte preserved; phase1 backups are in `phase1_archive/`.

Night look: `./blender-4.5.3-linux-x64/blender -b assets.blend -t 4 --python-exit-code 1 --python render_hero_night.py` produces `hero_night.png` (24 denoised samples) without saving changes to the blend.

## Hero night cockpit

From this directory, with Blender 4.5 on your path:

```sh
blender -b assets.blend -t 4 --python-exit-code 1 --python build_cockpit.py -- --render
blender -b assets_night.blend -t 4 --python-exit-code 1 --python validate_cockpit.py
```

The first command saves `assets_night.blend` with all four assets and then renders `hero_cockpit_preview.png` at 1280 × 800 using 24 denoised CPU Cycles samples and four fixed threads. Omit `--render` to save the blend only. The open file shows Hero and `Preview_Cockpit`. The preview collection contains the driver-eye camera, lights, road, and marker meshes. Remove the collection and assign your shot camera and world for production. Validation writes `cockpit_validation.json` and also accepts `assets.blend` as input. It measures exterior and interior bounds in Hero root coordinates from evaluated mesh, curve, and text vertices, excluding empties.

To use on a local Hero already in a shot, run this in Blender Python from the script directory:

```python
from runpy import run_path

apply_night = run_path("hero_night_materials.py")["apply_hero_night_materials"]
build_cockpit = run_path("build_cockpit.py")["build_cockpit"]
materials = apply_night()
cockpit = build_cockpit()
```

The material function returns the `paint` and `glass` material datablocks. The default `glass="clear"` uses Principled transmission weight 1, roughness 0.025, and IOR 1.04 for the existing single-surface panes in Cycles. Use `glass="dark"` for the opaque night exterior look. The cockpit builder uses a private deck mesh and opens the center beneath the canopy between Y −1.15 m and +0.65 m. Run the builder in a shot or variant file and save under that file's name.

Append the top-level **Hero** collection from `assets_night.blend` to bring in the cockpit child collection with its original parent. If your append workflow imports collections individually, keep Hero and its cockpit from the same append operation. Appending **Hero_Cockpit** alone can pull in a parent dependency and leave you with a second root when Hero is already present. For a shot with Hero already appended from `assets.blend`, run the two helpers on that Hero. Both accept `root=your_hero_root` for renamed imports.

`Hero_Root → Hero_CockpitRoot → Hero_MapAnchor`. The cockpit root is at identity under Hero. The map anchor is at **(0.000, −0.040, 0.715) m** in Hero root coordinates, with zero rotation and unit scale. Align the hologram to the anchor's local **XY** plane, with **+Y** forward and **+Z** as the upward normal. The preview camera sits at the left driver’s eye at **(−0.327, −0.530, 0.966) m** and aims toward **(−0.290, 0.680, 0.876) m** in Hero root coordinates.

### Cockpit runtime verification

Actually built and saved `assets_night.blend`; `hero_cockpit_preview.png` is the final driver-eye true Blender render. `hero_cockpit_shoulder.png` retains the first rear-shoulder preview. Build/render and validator exited 0; 40/40 dedicated checks passed, using true evaluated geometry vertex bounds. Original `assets.blend` SHA-256 remains `4abbfbffba861de309978fdc225d803ac6cadf38273c151547c73e1baa7cd00f`. See `cockpit_delivery_report.txt` and `cockpit_validation.json`. This is a lightweight interior; validate the final animated windshield-crossing camera path in the shot.
