#!/bin/bash
set -euo pipefail
if [ "${STRAY_ALLOW_UNREVIEWED_FULL_PREVIEW:-0}" != 1 ]; then echo "STOP: old full preview failed narrative review; only repair segments are permitted until coordinator acceptance" >&2; exit 2; fi
cd /workspace/stray/production
echo "$$" > codex_preview.pid
printf '{"stage":"render","supervisor_pid":%s}\n' "$$" > codex_job.json
trap 'printf "{\"stage\":\"stopped_or_failed\",\"supervisor_pid\":%s}\n" "$$" > codex_job.json' EXIT
/workspace/stray/blender-4.2.0-linux-x64/blender -b -t 4 --python-exit-code 1 --python build_scene.py -- --mode animatic --asset-mode codex --asset-file /workspace/stray/production/hero_asset_snapshot.blend > codex_animatic.log 2>&1 &
render_pid=$!
echo "$render_pid" > codex_blender.pid
wait "$render_pid"
printf '{"stage":"encode","supervisor_pid":%s}\n' "$$" > codex_job.json
./encode_preview.sh codex_v4 /workspace/stray/previews/animatic_frames_codex > codex_encode.log 2>&1
printf '{"stage":"complete","supervisor_pid":%s,"video":"/workspace/stray/previews/STRAY_codex_v4_640x360_12fps.mp4"}\n' "$$" > codex_job.json
trap - EXIT
