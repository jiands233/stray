# Targeted v6 handoff — all are review proofs, not final acceptance

## Actual videos
- street_curl.mp4:36–40s,4s,640x360/12fps,48 real3D Workbench frames. Static contiguous road first; only650–710m road region curls starting36.8s after Hero is clear. Marked surface faces camera; pursuing Police rides a segment, falls and explodes behind. Hero0 off-frame centers,0 non-Hero center-ray occlusions across48frames. Full-action readability remains coordinator review, not inferred from these metrics.
- spotlight.mp4:24.2–28.2s,4s,480x270/8fps,32 real Eevee frames. Actual SPOT emitter on delivered helicopter underside, road-distance falloff and shadows; no gray ellipse proxy.
- cockpit_entry.mp4:31–33s,2s,480x270/12fps,24 real Eevee frames. Actual Codex cockpit and private deck opening; body and glass retained.
- cockpit_exit.mp4:34–36s,2s,480x270/12fps,24 real Eevee frames. Same windshield path in reverse, never through rear seats/window.

## Body-local camera proof
World position = Hero_Root.matrix_world @ local_position. Entry localX=-.327m,Z=.966m,Y1.650→-.530m; exit reverses that exact line. QA inverse matrices reproduce endpoints within0.00003m. Inside pause shares all Hero_Root transforms; orientation pans in place toward dash, not an orbit around car. Camera/glass/body not hidden during passage. Parent must still dynamically inspect it.

## Actual assets / materials
Delivered Police/Heli/Truck appended from stable production/fleet_snapshot_v6.blend; no Preview rigs; wheels rotate localX, main rotorZ, tail rotorX. One actual Hero_Root retained. Approved material helper and build_cockpit(root=Hero_Root) applied in own scene, source codex directory untouched. STRAY/NIGHT DRIVE demo text blanked; numeric instruments retained. Center screen route UI still needs replacing blank demo area; prototype anchor route exists but not yet accepted visually. For fast Eevee windshield proofs, static clean BLENDED alpha0.10 tinted glass is used instead of costly physical refraction; no animated transparency or hidden body. Workbench street does NOT reproduce transmissive-glass appearance, so its pale canopy is not paint validation. Actual Eevee images show night paint.

## True1920x1080 paired benchmark
Same frame22.4, same Hero/fleet/city/weather geometry, three configured Blender threads, no competing own render, raytracing already off. No frame interpolation and no resolution reduction.
- quality32:28.5495s;32samples, original sunlight shadows,3 moving area lights, compositor glow.
- fast4:6.2012s;4samples, shadows off, one area light disabled(2 remain), glow off.
- 4.604x measured speedup for this view only. Files benchmark1080_quality32.png / benchmark1080_fast4.png; comparison benchmark_comparison.jpg.
- Visual cost observed: lost magenta road/body fill, less halo/bloom, flatter contact/depth; low-sample moving-edge shimmer not tested. Story geometry untouched. Current scene3080objects/1689meshes; material-batched city and shared Police copies already used. No claim of a final6.2h completion time: single exterior view is not whole-film average, cabin transparency/FX may cost more. Cabin proof entry24frames took165.55s and exit24 took145.72s including updates/QA/first shader setup.
- Original41h extrapolation is obsolete as a deadline; it was a different, concurrent proxy test. Paired numbers above are the valid local comparison.

## Gate
No full preview rerun, final1080p60 render or bake started. Previously accepted ending/collision clips untouched. Please review these4clips before any full-length run. AI ad art/surface finish and audio audition remain pending. Audio still includes German police siren and firework-based explosion, not certified NYPD/real vehicle explosion.
