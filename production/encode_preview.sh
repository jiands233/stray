#!/bin/bash
set -euo pipefail
name=${1:-proxy_v3}
frames=${2:-/workspace/stray/previews/animatic_frames_v3}
out=/workspace/stray/previews/STRAY_${name}_640x360_12fps.mp4
ffmpeg -hide_banner -y -framerate 12 -start_number 0 -i "$frames/%05d.png" -i /workspace/stray/audio/preview_mix.wav -vf 'fade=t=out:st=58:d=2' -t 60 -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart "$out"
ffprobe -v error -show_entries format=duration,size:stream=index,codec_name,width,height,r_frame_rate,nb_frames -of json "$out" > "${out%.mp4}_probe.json"
echo "$out"
