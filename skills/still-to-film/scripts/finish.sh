#!/usr/bin/env bash
# The raw ffmpeg finish used on HOME, for reference (scripts/finish.py builds the same thing from arguments).
# usage: bash finish.sh raw.mp4 final.mp4
set -e
IN=$1; OUT=$2
V="format=gbrp,"                                                               # colour work in RGB
V+="eq=saturation=0.78:enable='between(t,4.32,5.76)',colorbalance=rm=-0.04:bm=0.04:enable='between(t,4.32,5.76)',"   # one warm, oversaturated still
V+="noise=alls=5:allf=t:enable='between(t,2.40,4.32)',"                       # extra grain on a clean CG insert
V+="colorbalance=rs=-0.025:gs=-0.005:bs=0.04:rh=0.035:gh=0.01:bh=-0.03,"     # film look: cool shadows, warm highlights
V+="eq=contrast=1.04:saturation=0.97,noise=alls=3:allf=t,vignette=angle=PI/5.8,"
V+="scale=out_color_matrix=bt709:out_range=tv,format=yuv420p"
A="[0:a]afade=t=out:st=117.12:d=5.76:curve=qsin,volume=-3dB[a]"             # music only, fades from the title
ffmpeg -v error -y -i "$IN" -filter_complex "[0:v]${V}[v];${A}" -map "[v]" -map "[a]" \
  -c:v libx264 -crf 19 -preset slow -maxrate 16M -bufsize 32M -color_primaries bt709 -color_trc bt709 -colorspace bt709 \
  -c:a aac -b:a 256k -movflags +faststart "$OUT"
echo "wrote $OUT"
