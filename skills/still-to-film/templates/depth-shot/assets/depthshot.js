// depthshot.js — depth-parallax shots for HyperFrames (or any seekable GSAP timeline).
// A still + its depth map rendered through a virtual camera in WebGL2. Deterministic: every frame is a pure
// function of timeline time; motion blur = averaged sub-frames. Part of the still-to-film skill (MIT), built for HOME.
//
// depthShot({
//   canvas: 'shot-gl',            // id of a <canvas> (WebGL2), sized to the composition
//   plate: 'tex-plate',           // id of a decoded <img>: the colour still (upscale it first: scripts/prep_plate.py)
//   depth: 'tex-depth',           // id of a decoded <img>: depth map, near = bright, 8-bit grey
//   t0, dur,                      // shot start and length on the timeline (seconds); u = (t - t0) / dur in [0, 1]
//   cam: u => ({vx, vy, lz, roll, px, py, pz}),
//        // vx, vy : view centre in plate uv (0.5, 0.5 = centre)
//        // lz     : ln(zoom). 0 = plate fills the frame; 0.69 = 2x
//        // roll   : degrees around the view centre (HOME's crane shot rolled 0 -> -30). Preview the sign first
//        // px, py : parallax shift per depth unit (truck / pedestal). Near pixels move more than far ones
//        // pz     : extra magnification per depth unit around dref (what makes a push a dolly, not a zoom)
//   dref: 0.5,                    // depth that stays put (put it on the subject); default 0.5
//   sub: 6, shutter: 1/60,        // motion-blur sub-frames and shutter length (seconds)
//   water: 'tex-water', flow: [x, y], flowAmt: 0.004,   // optional: flowing water + glints inside a mask
//   sway: 'tex-sway', swayFn: t => [x, y],              // optional: masked region displaced by swayFn(t)
//   energy: 'tex-energy',                               // optional: light pulses travelling up a line mask
//   sprites: [{ img: 'tex-ship', at: (u, t) => ({x, y, d, size, rot, alpha}) }],   // cut-outs projected by the same camera
//   timeline: tl,                 // the paused GSAP timeline to attach to (default: global `tl`)
// })
// Call it only after every <img> it uses has decoded, then register the timeline. See templates/depth-shot/.
const DS_VERT = `#version 300 es
in vec2 aPos; out vec2 vUv;
void main(){ vUv = aPos * 0.5 + 0.5; gl_Position = vec4(aPos, 0.0, 1.0); }`;
const DS_FRAG = `#version 300 es
precision highp float;
in vec2 vUv; out vec4 o;
uniform sampler2D uPlate, uDepth, uWater, uSway, uEnergy;
uniform vec2 uV, uPar, uFlow, uSwayV; uniform float uZ, uRoll, uPz, uDref, uAsp, uT, uFlowAmt, uHasWater, uHasSway, uHasEnergy;
vec2 toI(vec2 v){ return vec2(v.x * uAsp, v.y); }
vec2 fromI(vec2 v){ return vec2(v.x / uAsp, v.y); }
vec2 rot(vec2 v, float a){ float c = cos(a), s = sin(a); return vec2(c * v.x - s * v.y, s * v.x + c * v.y); }
vec2 bwd(vec2 p, float d){ return uV + fromI((rot(toI(p - 0.5), -uRoll) - uPar * (d - uDref)) / (uZ * (1.0 + uPz * (d - uDref)))); }
float h21(vec2 p){ p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
float vn(vec2 p){ vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
  return mix(mix(h21(i), h21(i + vec2(1, 0)), f.x), mix(h21(i + vec2(0, 1)), h21(i + vec2(1, 1)), f.x), f.y); }
void main(){
  vec2 p = vec2(vUv.x, 1.0 - vUv.y);
  vec2 s = bwd(p, uDref);
  for (int i = 0; i < 14; i++) { float d = texture(uDepth, s).r; s = bwd(p, d); }
  if (uHasSway > 0.5) { float m = texture(uSway, s).r; s -= uSwayV * m; }
  vec3 c;
  float w = 0.0;
  if (uHasWater > 0.5) {
    w = texture(uWater, s).r;
    vec2 q = s * vec2(95.0, 260.0) - uFlow * uT * 13.0;
    vec2 off = (vec2(vn(q), vn(q + 17.3)) - 0.5) * uFlowAmt * w;
    c = texture(uPlate, s + off).rgb;
    float sp = pow(vn(s * vec2(260.0, 520.0) - uFlow * uT * 30.0), 10.0) * w;
    c += sp * 0.9 * vec3(1.0, 0.86, 0.6) * smoothstep(0.25, 0.7, dot(c, vec3(0.33)));
  } else {
    c = texture(uPlate, s).rgb;
  }
  if (uHasEnergy > 0.5) {
    float e = texture(uEnergy, s).r;
    float glow = textureLod(uEnergy, s, 3.5).r;
    float col = floor(s.x * 900.0);
    float ph = fract(s.y * 7.0 + uT * 0.45 + h21(vec2(col, 3.1)));
    float ph2 = fract(s.y * 19.0 + uT * 1.05 + h21(vec2(col, 7.7)));
    float pulse = pow(1.0 - ph, 9.0) + 0.45 * pow(1.0 - ph2, 14.0);
    vec3 ec = vec3(1.0, 0.82, 0.52);
    c += min(ec * (e * (0.15 + 1.6 * pulse) + glow * 0.8 * pulse), vec3(0.75));
  }
  o = vec4(c, 1.0);
}`;
const SP_VERT = `#version 300 es
in vec2 aPos; uniform vec2 uC, uS; uniform float uR; out vec2 vUv;
void main(){ vUv = aPos * 0.5 + 0.5; vec2 v = aPos * uS; float c = cos(uR), s = sin(uR);
  v = vec2(c * v.x - s * v.y, s * v.x + c * v.y); gl_Position = vec4(uC + v, 0.0, 1.0); }`;
const SP_FRAG = `#version 300 es
precision highp float; in vec2 vUv; out vec4 o; uniform sampler2D uTex; uniform float uA;
void main(){ vec4 t = texture(uTex, vec2(vUv.x, 1.0 - vUv.y)); o = vec4(t.rgb * t.a * uA, t.a * uA); }`;

function dsLerpKeys(keys, u) {
  if (u <= keys[0][0]) return keys[0].slice(1);
  for (let i = 1; i < keys.length; i++) {
    if (u <= keys[i][0]) {
      const a = keys[i - 1], b = keys[i], t = (u - a[0]) / (b[0] - a[0]);
      const e = t * t * (3 - 2 * t);            // smooth between keys
      return a.slice(1).map((v, k) => v + (b[k + 1] - v) * (keys.length > 2 ? e : t));
    }
  }
  return keys[keys.length - 1].slice(1);
}

function depthShot(opt) {
  // opt: {canvas, plate, depth, water?, sway?, t0, dur, cam(u), dref, sub, shutter, swayFn(t)->[x,y], flow:[x,y], flowAmt,
  //       sprites:[{img, at(u)->{x,y,d,size,rot,alpha} }]}
  const cv = document.getElementById(opt.canvas);
  const gl = cv.getContext('webgl2', { preserveDrawingBuffer: true, premultipliedAlpha: false, antialias: true });
  const mk = (type, src) => { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s)); return s; };
  const prog = (v, f) => { const p = gl.createProgram(); gl.attachShader(p, mk(gl.VERTEX_SHADER, v)); gl.attachShader(p, mk(gl.FRAGMENT_SHADER, f));
    gl.linkProgram(p); return p; };
  const P = prog(DS_VERT, DS_FRAG), S = prog(SP_VERT, SP_FRAG);
  const buf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
  const tex = (img, mip) => { const t = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, t);
    gl.pixelStorei(gl.UNPACK_COLORSPACE_CONVERSION_WEBGL, gl.NONE);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img);
    if (mip) gl.generateMipmap(gl.TEXTURE_2D);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, mip ? gl.LINEAR_MIPMAP_LINEAR : gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    return t; };
  const el = (id) => document.getElementById(id);
  const tPlate = tex(el(opt.plate), true), tDepth = tex(el(opt.depth), false);
  const tWater = opt.water ? tex(el(opt.water), false) : tDepth, tSway = opt.sway ? tex(el(opt.sway), false) : tDepth;
  const tEnergy = opt.energy ? tex(el(opt.energy), true) : tDepth;
  const sprites = (opt.sprites || []).map(s => ({ ...s, tex: tex(el(s.img), true), asp: el(s.img).naturalWidth / el(s.img).naturalHeight }));
  const U = (n) => gl.getUniformLocation(P, n), US = (n) => gl.getUniformLocation(S, n);
  const asp = cv.width / cv.height, dref = opt.dref ?? 0.5, sub = opt.sub ?? 6, shutter = opt.shutter ?? 0.5 / 30;
  const fwd = (c, x, y, d) => {           // plate uv -> clip space, same camera as the shader
    const k = Math.exp(c.lz) * (1 + c.pz * (d - dref));
    let vx = (x - c.vx) * asp * k + c.px * (d - dref), vy = (y - c.vy) * k + c.py * (d - dref);
    const r = c.roll * Math.PI / 180, cs = Math.cos(r), sn = Math.sin(r);
    const rx = cs * vx - sn * vy, ry = sn * vx + cs * vy;
    return { x: (rx / asp) * 2, y: -ry * 2, k };
  };
  const drawAt = (tl_t) => {
    const u = Math.min(1, Math.max(0, (tl_t - opt.t0) / opt.dur));
    const c = opt.cam(u);
    gl.viewport(0, 0, cv.width, cv.height);
    gl.useProgram(P);
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    const loc = gl.getAttribLocation(P, 'aPos'); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    [[tPlate, 'uPlate'], [tDepth, 'uDepth'], [tWater, 'uWater'], [tSway, 'uSway'], [tEnergy, 'uEnergy']].forEach(([t, n], i) => {
      gl.activeTexture(gl.TEXTURE0 + i); gl.bindTexture(gl.TEXTURE_2D, t); gl.uniform1i(U(n), i); });
    gl.uniform2f(U('uV'), c.vx, c.vy); gl.uniform1f(U('uZ'), Math.exp(c.lz)); gl.uniform1f(U('uRoll'), c.roll * Math.PI / 180);
    gl.uniform2f(U('uPar'), c.px, c.py); gl.uniform1f(U('uPz'), c.pz); gl.uniform1f(U('uDref'), dref); gl.uniform1f(U('uAsp'), asp);
    gl.uniform1f(U('uT'), tl_t); gl.uniform1f(U('uHasWater'), opt.water ? 1 : 0); gl.uniform1f(U('uHasSway'), opt.sway ? 1 : 0); gl.uniform1f(U('uHasEnergy'), opt.energy ? 1 : 0);
    const fl = opt.flow || [0, 1]; gl.uniform2f(U('uFlow'), fl[0], fl[1]); gl.uniform1f(U('uFlowAmt'), opt.flowAmt ?? 0.004);
    const sw = opt.swayFn ? opt.swayFn(tl_t) : [0, 0]; gl.uniform2f(U('uSwayV'), sw[0], sw[1]);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    if (sprites.length) {
      gl.useProgram(S); const sl = gl.getAttribLocation(S, 'aPos'); gl.enableVertexAttribArray(sl); gl.vertexAttribPointer(sl, 2, gl.FLOAT, false, 0, 0);
      for (const sp of sprites) {
        const a = sp.at(u, tl_t); if (!a || a.alpha <= 0) continue;
        const q = fwd(c, a.x, a.y, a.d);
        const hw = a.size * q.k, hh = hw / sp.asp * asp;
        gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, sp.tex); gl.uniform1i(US('uTex'), 0);
        gl.uniform2f(US('uC'), q.x, q.y); gl.uniform2f(US('uS'), hw, hh); gl.uniform1f(US('uR'), -(a.rot + c.roll) * Math.PI / 180);
        gl.uniform1f(US('uA'), a.alpha);
        gl.enable(gl.BLEND); gl.blendFuncSeparate(gl.ONE, gl.ONE_MINUS_SRC_ALPHA, gl.ZERO, gl.ONE);
        gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4); gl.disable(gl.BLEND);
      }
    }
  };
  // Motion blur: draw each sub-frame into an FBO, then blend it onto the canvas as a running average.
  // Blend COLOUR ONLY (alpha factors ZERO, ONE): blending the canvas alpha too makes the whole shot darker.
  const fbo = gl.createFramebuffer(), ftex = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, ftex); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, cv.width, cv.height, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
  gl.bindFramebuffer(gl.FRAMEBUFFER, fbo); gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, ftex, 0);
  gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  const CP = prog(DS_VERT, `#version 300 es
precision highp float; in vec2 vUv; out vec4 o; uniform sampler2D uT; uniform float uA;
void main(){ o = vec4(texture(uT, vUv).rgb, uA); }`);
  const render = (t) => {
    gl.bindFramebuffer(gl.FRAMEBUFFER, null); gl.clearColor(0, 0, 0, 1); gl.clear(gl.COLOR_BUFFER_BIT);
    for (let k = 0; k < sub; k++) {
      const tt = t + (sub > 1 ? (k / (sub - 1) - 0.5) * shutter : 0);
      gl.bindFramebuffer(gl.FRAMEBUFFER, fbo); drawAt(tt);
      gl.bindFramebuffer(gl.FRAMEBUFFER, null);
      gl.useProgram(CP); const l = gl.getAttribLocation(CP, 'aPos'); gl.bindBuffer(gl.ARRAY_BUFFER, buf);
      gl.enableVertexAttribArray(l); gl.vertexAttribPointer(l, 2, gl.FLOAT, false, 0, 0);
      gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, ftex); gl.uniform1i(gl.getUniformLocation(CP, 'uT'), 0);
      gl.uniform1f(gl.getUniformLocation(CP, 'uA'), 1 / (k + 1));
      gl.enable(gl.BLEND); gl.blendFuncSeparate(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA, gl.ZERO, gl.ONE);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4); gl.disable(gl.BLEND);
    }
  };
  const proxy = { t: opt.t0 };
  render(opt.t0);
  const T = opt.timeline || window.tl;
  if (!T) throw new Error('depthShot: pass {timeline} or define a global `tl`');
  T.to(proxy, { t: opt.t0 + opt.dur, duration: opt.dur, ease: 'none', onUpdate: () => render(proxy.t) }, opt.t0);
  return { render };
}
