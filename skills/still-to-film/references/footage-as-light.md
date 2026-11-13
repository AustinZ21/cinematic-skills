# Footage as light: project moving images onto real form

A method for combining generated or procedural footage with 3D so that each does only what it is good at.
The footage is never shown as a picture. It is used as a light source and thrown onto a blank object in a real
scene. Distilled from aicreataro's making-of (see `NOTICE.md`); the tools he names are examples, any provider or
your own renders will do.

## The idea

Every source has a weakness that shows when it is asked to carry the whole frame:

| Source | Good at | Bad at |
|---|---|---|
| Generated or procedural footage | rich texture, colour, organic motion | stable form, consistent geometry, holding up to a moving camera |
| 3D (modelled, scanned or generated mesh) | form, perspective, occlusion, a camera that can go anywhere | surface richness; looks plain or plastic without a lot of work |
| Simulated light and atmosphere | depth, mood, beams, shadow | has nothing to say on its own |

So split the jobs. **Form** comes from 3D. **Surface** is left blank. **Image** arrives as light. **Air** makes the
light visible. Flicker, morphing and drift in the footage stop being errors, because light on a surface is expected
to flow. The general rule behind it: *put an unreliable source where its failures read as texture.*

## The five roles

1. **Form.** One strong object with a readable silhouette and real relief (a statue, a product, a logo, a face, a
   building). Where it comes from doesn't matter: modelled in code, scanned, or made by an image-to-3D service.
2. **Blank surface.** A matte, near-white, slightly rough material. No texture of its own. It is a screen with shape.
   Dark or glossy surfaces swallow the projection; use them only on purpose.
3. **Reels.** The moving images to project: generated clips, your own renders (fluid, fire, aurora, type), archive.
   High contrast and saturated colour survive projection; fine detail does not. Edit them into reels **before**
   they go into 3D, cut on the music's grid, so the light itself changes on the beat.
4. **Projectors.** Lights that carry a reel as their colour. Two from different sides is the useful minimum: one
   key, one opposite in a contrasting palette, so the form is modelled by where the two meet and where neither
   reaches. Narrow cones aimed at the object, not floodlights.
5. **Room and air.** A dark space so only projected light exists, and haze so the beams are visible between the
   projector and the object. The haze is what tells the viewer this is light and not a texture.

Then a **camera** treats it as a real set: a few fixed or slowly moving positions, cut on the grid. And optionally a
**handover**: the last frame can be given to an image-to-video model so the object itself starts to move. Do this
only at the end; once the form moves, it is no longer under 3D control.

## Building it (Blender, headless; see `blender-route.md`)

- Object: import or build, apply the blank material, centre it, give it a floor or plinth to catch spill.
- Projector: a spot light whose colour comes from an image-sequence or movie texture mapped in the light's own
  coordinates, so the picture leaves the lamp like a slide. Drive the frame offset from the scene frame; keep the
  reel's frame rate equal to the scene's.
- Air: a volume with low density filling the room. Raise density until the beams read, stop before the object greys out.
- World: black. Any ambient light flattens the effect.
- Samples: volumes are noisy. Test one frame at final settings early to learn the per-frame time before planning length.

The same idea works in a browser renderer with a projective texture on a spotlight and a ray-marched beam, at lower
cost and lower realism. Choose by the table in `blender-route.md`.

## Decisions to make before building

| Question | Guidance |
|---|---|
| What is the object, and why this one? | It should mean something to the piece; the projection is its costume, not its subject. |
| What do the reels show? | Things that relate to the object or contrast with it (stone ↔ water, logo ↔ the elements it stands for). 3 to 6 looks is plenty. |
| How do the two projectors differ? | Palette (warm / cool) and content. If both show the same thing, use one. |
| What does the camera do? | One sealed move or a static per shot; change position on the grid. Let the light be the motion. |
| Where is the still moment? | One beat with a single projector, or none, before the last look. |
| How does it end? | Hold, go dark, or hand over the last frame for the object to move. |

## Review

- Does the form still read with the footage on it? If not: fewer projectors, narrower cones, simpler reels.
- Are the beams visible? If not: more haze, darker room, or a camera angle that looks across the beam.
- Does the light change on the beat? Check reel cut times against the music's hit times, not by eye.
- Is any frame just a flat picture of the footage? Then the camera is looking straight down a projector; move it.
- Show a breakdown when sharing: final, the scene with projectors and camera visible, and the reels playing. The
  method is part of the appeal.

## Variations

- Project the piece's own earlier shots onto its final object (a logo wearing the film that led to it).
- Project type or data instead of footage; the object becomes a display.
- Swap roles: a textured object lit by plain moving light (gobos, caustics) for a quieter version.
- Several objects, one projector: the image is only complete from one camera position.
