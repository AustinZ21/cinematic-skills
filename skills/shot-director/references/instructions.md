# Turning a move into an executable instruction

The six things every move needs, choreography for multi-move shots, and the staged long-take structure.

"Use a push in" still leaves the model guessing: from where to where, how fast, following whom, and when it stops. Every move needs six things:

1. **Name:** push in, pan, truck, tracking…
2. **Direction:** forward, back, left, right, up, down, clockwise
3. **Speed:** slow, steady, sudden, fast then slowing
4. **Object:** who it follows, who it centres on, from what to what
5. **Start and end frames:** which size and framing it begins on, where it ends
6. **Stability and limits:** smooth or handheld, does the focal length change, does the subject's size hold

Before:

> The camera moves slowly, cinematic.

After:

> Eye-level medium shot, 50mm, shallow depth of field. The surgeon walks toward the medbay. The camera backs away in front of him, holding three metres and a chest-up frame the whole time, at his walking pace. Camera height, focal length and his size stay constant; the camera stops when he stops at the medbay doors.

Every phrase has a job. Size and lens set the frame. "Backs away in front of him" sets the route. Three metres and chest-up set the follow. The last sentence sets the end.

### Complex moves are choreography

For anything with more than one move, write four things:

- **Main move:** the most important path in the shot
- **Secondary move:** a second action that happens only at one point
- **Trigger:** a subject action or a place in space
- **Holds:** subject size, eye line, focus, axis, continuity

Before:

> The camera follows the girl, then moves in front of her.

After:

> The camera follows the cadet from her left rear at a steady one and a half metres. As she passes the second support pillar, it speeds up, overtakes on her left and arcs a quarter circle to her front, then backs away in a lead. She goes from a back view to a frontal medium shot naturally; direction stays consistent; the shot is continuous.

"The second support pillar" is the trigger. Without it, the model tends to blend the follow and the orbit from the first frame.

**The rule: a short shot gets at most two main moves.** Five to eight seconds fits a follow plus one orbit. Climbing, rolling and flying through a window go in the next shot.

For staged long takes, structure it like this:

> Stage 1: where it starts, which move, approaching whom
> Trigger: what the subject does, or where the camera arrives
> Stage 2: the new path, and what it reveals
> Trigger: what happens
> End: the shot size and framing it settles on

---

### Clip length

Generative video models produce clips of a few seconds (often 4 to 10). For a shot shorter than the model's minimum, prompt the full clip with the move completing early and trim on the beat in the edit. For a shot longer than the maximum, split it at a trigger and make the second clip start exactly where the first ended.
