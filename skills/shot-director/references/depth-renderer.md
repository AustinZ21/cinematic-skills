# Mapping moves onto a still-image depth renderer

For films built from still images with a depth-parallax camera (see the `still-to-film` skill). How the vocabulary maps onto renderer controls, and the limits of a single still.

HOME was built from still images, not generated video, so its camera is a small WebGL renderer reading a depth map. Its controls line up with this vocabulary almost one to one:

- **`lz` (scale)** on its own is a zoom: flat, even, no parallax.
- **`pz` (depth-weighted scale)** is what makes it a dolly: near things grow faster than far things. A real push is `lz` and `pz` together.
- **`px` / `py` (parallax offset)** are truck and pedestal.
- **`roll`** is a barrel roll, or a Dutch angle if it stops and holds.
- **`vx` / `vy` (view centre)** reframe across the image; it reads as a small pan or tilt.
- **Dolly zoom** falls out for free: raise `pz` while holding `lz`, with the reference depth on the subject, so the subject keeps its size while the background warps.

What a single still can't do: big pans and orbits run out of picture, and too much parallax tears the image, which is exactly what happened on the crane shot. Keep to quarter moves and let things move inside the frame instead. Rack focus is possible with a depth-weighted blur, but we haven't built it yet.

The working rules for the next film:

1. **Write each shot in the six layers** in the spec before building it.
2. **One main move per shot**, two at most with a trigger. Everything else is a cut.
3. **Every move has a start, an end and a hold.** No open-ended "push in".
4. **Notes in the same language:** shot, timestamp, move, direction, start → end, speed, what stays still. "s14, 31–43 s: push toward the end window, faster; roll left to −30°; container stays put."
5. **Static first when unsure.** Then add one move and see what it actually adds.
6. **Decide the clocks before the shots:** story time, screen time, rhythm. Lock the rhythm to the music's beat grid.
7. **Every wide shot gets a scale reference;** every sequence keeps one screen direction.
8. **Every shot changes what the audience knows or feels.** If it doesn't, cut it.

---
