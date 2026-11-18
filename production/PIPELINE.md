# STRAY production interface

Status: real Blender 4.2 CPU software-Eevee pipeline in development. No GPU detected. 8 vCPU, 15GiB shared RAM, 112GiB free at audit. Standalone Blender at /workspace/stray/blender-4.2.0-linux-x64/blender. Apt repository unavailable; official binary works. Empty-scene 640x360 first Eevee frame: 22.23 seconds including shader startup. No production render previously running.

## Asset contract (Codex)
Do not clear scene. Asset builders: build_hero(), build_police(), build_helicopter(), build_tanker(). Asset file /workspace/stray/assets/codex/assets.blend. Collections Hero, Police, Heli, Truck. Roots Hero_Root, Police_Root, Heli_Root, Truck_Root. Units meters, +Z up, +Y front, X lateral. Root at ground-center. Hero 4.8m long, 2m wide, 1.2m high; tires contact Z0. Wheels, lights, glass and rotor independent. Prefer material diffuse_color matching shader base for Workbench animatic. No volumetric shaders/no glass noise; clean opaque tinted glass with cabin visible from interior camera.

## World/camera/time
60 seconds, final 3600 actual rendered frames at 60fps, 1920x1080. Preview 640x360, 12 actual renders/sec (explicit animatic, NOT final60 nor interpolated). One continuous actual avenue +Y, starting alley y0 to y30, tanker crossing y370, barricade y590, curling road y650–800, elevated light ribbon y850–1050, broken screen y1040, cliff y1130, flight canyon y1200–1500. All obstacles exist in actual world. Camera relative positions and look targets interpolated continuously, upright; no visibility-based teleports. World time slowed by common mapping for rain/rotors/lights/effects/vehicles, camera remains continuously moving.

## Stages
1. Proxy geometry + city + complete camera/action timing. Three Eevee test frames and honest measured render time.
2. Small complete Workbench material-color animatic, 12fps explicitly identified. Review continuity and staging before final render.
3. Append Codex collections and replace proxies without touching asset directory. Update dashboard/interior if needed.
4. Final only after supervisor acceptance. No high-cost full render now.

## Constraints
No live-action imagery; no video generative tools. AI-generated billboard textures only, currently missing after interrupted request; geometry and shader stand-ins stay explicitly labeled as placeholders. No titles/subtitles/end English. Real recorded SFX only; exact105BPM continuous licensed electronic track remains research task, never fabricate certification. Record all sources/licenses in audio/SOURCES.md.

## Updated measured status
First 640x360 Eevee proxy test: firstframe5.91s, warm2.55–2.57s at8samples (not final quality). Original preview: 720 real Workbench frames at320x180/12fps,100.6s total; first QA found alley-wall camera occlusion and unwanted visibility inheritance. Both addressed in v2; v2 is640x360 and is the review candidate. Workbench preview has no camera/object interpolation masquerading as final60.
Audio acquired: Ferrari ZoomH6, German police mobile recording, helicopter ZoomH6(CCBY4), firework Tascam recording, Craig Smith plate-glass recording. Music Alive/PunchDeck is publisher-labeled105BPM(CCBY3), real continuous60s segment; drop waveform aligned10.285714, pre-drop silence not yet verified. See audio/SOURCES.md and mix_manifest.json.

## Handoff / current review deliverables
- Complete proxy v3 video: /workspace/stray/previews/STRAY_proxy_v3_640x360_12fps.mp4 — verified60.000s,720 rendered frames, H264+AAC,640x360/12fps; original105BPM-labeled music and recorded-SFX rough mix.
- Appended only collection Hero from Codex assets successfully using Blender4.2; no Preview imported. Three actual Eevee integration frames: previews/codex_test_04.50s.png, codex_test_22.40s.png, codex_test_46.00s.png.
- Frozen immutable read snapshot production/hero_asset_snapshot.blend with source metadata/hash in asset_snapshot.json; source assets/codex untouched. This avoids concurrent asset-write conflicts.
- Integrated v4 full animatic running via run_codex_preview.sh. Actual PIDs in codex_preview.pid / codex_blender.pid. Log codex_animatic.log; per-frame progress.json; post-render auto-encode and probe. Result previews/STRAY_codex_v4_640x360_12fps.mp4. Read codex_job.json for complete state.
- To stop only this production, send TERM to PID in codex_blender.pid, then to supervisor if needed; do not kill all Blender processes (Codex shares machine). Resume with run_codex_preview.sh; completed PNGs validated before skip.
- Only one integrated low-res render currently active; no high-cost final render. 3 worker threads default via STRAY_THREADS, no GPU.

## Important scene-file caveat
Saved .blend is a staging snapshot, NOT a fully baked timeline. Complete motion is in build_scene.py update(t), evaluated each actually rendered frame. Reproduce with script, not by opening snapshot and pressing Play. Final60fps rendering and baked-timeline handoff remain future gated steps, not already delivered.

## Current review gaps (do not claim final compliance)
Police/Heli/Truck are temporary proxies; Hero actual Codex asset integrated. AI billboard images missing after interrupted generation request; signs are procedural placeholders. Full comic surface treatment/impact frames incomplete. Interior is schematic. Camera and action causality still need full-motion review, particularly tanker/crash visibility and curling-road overhead framing. Music publisher says105BPM and waveform transition was aligned, but track has not been listened to; dramatic pre-drop silence not verified. Real siren is German rather than NYPD.

## Measured rendering budget
A real1920x1080 proxy frame at32Eevee samples took41.01s with another low-res job active. Linear3600-frame extrapolation ~41h; this is NOT a final cost promise and integrated Hero/fleet/art will change it. Integrated Hero640x360 warm32sample frames ~6.25s. Need optimize, quality review, and renewed benchmark before selecting final engine/samples. No frame interpolation is being used to pass12fps off as60.

## OVERRIDE after supervisor videoReview — 2026-11-18 Asia/Shanghai
Proxy v3 FAILED narrative acceptance. Integrated v4 was stopped at frame611/720 (own BlenderPID1051775, exit143); it is NOT a complete approved deliverable. Do NOT resume old full-length runner. Its default is now blocked pending explicit coordinator acceptance.
Priority is repaired short clips only: staging_v5.py, previews/repairs_v5/. Added physical cliff cut face/foundation, lower canyon floor and tower bases, actual building corridor/skybridges/light; physically placed interior steering wheel/dashboard/GPS/HUD; fixed-world tanker collision framing and collision-origin explosion; road-slab lane markings and arc; real helicopter SPOT light replacing painted patch. None has blanket acceptance: actual clips and per-frame camera_qa.json must be reviewed. Ads, surface polish and optimization benchmarks are paused per latest steering. No final render/bake initiated.

## Repair clips actually delivered
previews/repairs_v5 contains8 encoded short videos, each4–5s at640x360/12fps, not a full preview. Review first cliff_reveal(49–54), fall_ignition(53–58), flight_tunnel(56–60); overlaps prove same location/time. The last4s were actually rerendered once to correct a6-frame offscreen transition; identical overlap frames were copied between excerpt folders, never interpolated. Both ending clips now have0 out-of-frame Hero-center samples; supervisor motion review still required. Final flight clip includes normal2s final fade.
Street-curl clip FAILED self-review:33/60 frames have road-slab occlusion and10/60 Hero-center out-of-frame samples (some start inside cockpit). Do not mark it passed. New physical cockpit/GPS and tanker-origin colored blast are visible in actual test frames/clips, but entrance/collision sequencing still requires motion review. Actual searchlight lighting remains unproved in Workbench geometry clips. Latest fleet/material handoff received but deferred until geometry acceptance to avoid another full invalid render. No fresh optimization baseline or final schedule was produced. See HANDOFF_REPAIRS.json, repair_videos.json, REVIEW_FIRST.md.

## v6 targeted proofs complete
See HANDOFF_V6.json and previews/repairs_v6/REVIEW_FIRST.md. New delivered fleet, black-paint helper and actual Codex cockpit integrated. Strict Hero-local windshield entry/exit, actual-light spotlight clip and behind-Hero street curl delivered. Street48frames:0 offscreen Hero centers /0 non-Hero center-ray hits; perceptual acceptance still required. True1080 paired bench32samples28.5495s vs fast4samples6.2012s(4.604x), not a final-film runtime promise. No full preview/final/bake.
