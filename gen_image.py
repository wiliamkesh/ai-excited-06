#!/usr/bin/env python3
"""Generate 'The Sun That Opens' - make.fun ai-excited-01 round 11.

Procedural, fully deterministic (seeded) 1024x1024 artwork drawn with
Pillow only. No input images are read; every pixel is computed here.

Concept: an impossible giant sun cracked open like a cosmic door. Inside
the crack is a night sky - violet nebula, stars, a crescent moon - and one
giant luminous eye staring out. A tiny robot on a dark cliff leans back
against the pull, one hand shielding its face, the other reaching for
the light. Clouds bend inward toward the opening; debris streams into it.

This script writes out/entry.png and also regenerates main.ts, embedding
the PNG bytes so `node main.ts` reproduces the exact same file.
"""

import base64
import hashlib
import math
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

W = H = 1024
SEED = 11
random.seed(SEED)

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
OUT.mkdir(exist_ok=True)

SUN_C = (512, 430)
SUN_R = 305


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def vertical_gradient(w, h, stops):
    """stops: list of (pos 0..1, rgb)."""
    g = Image.new("RGB", (1, h))
    px = g.load()
    for y in range(h):
        t = y / max(1, h - 1)
        color = stops[-1][1]
        for i in range(len(stops) - 1):
            p0, c0 = stops[i]
            p1, c1 = stops[i + 1]
            if p0 <= t <= p1:
                f = 0.0 if p1 == p0 else (t - p0) / (p1 - p0)
                color = lerp(c0, c1, f)
                break
        px[0, y] = color
    return g.resize((w, h))


def radial_disc(size, stops):
    """Square RGB image, concentric-circle radial gradient (small then upscaled).

    stops: list of (pos 0..1 from center, rgb).
    """
    s = 256
    img = Image.new("RGB", (s, s), stops[-1][1])
    d = ImageDraw.Draw(img)
    cx = cy = s // 2
    steps = 96
    for i in range(steps, 0, -1):
        t = i / steps  # 0 center -> 1 edge
        color = stops[-1][1]
        for j in range(len(stops) - 1):
            p0, c0 = stops[j]
            p1, c1 = stops[j + 1]
            if p0 <= t <= p1:
                f = 0.0 if p1 == p0 else (t - p0) / (p1 - p0)
                color = lerp(c0, c1, f)
                break
        r = int((s // 2) * (i / steps))
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    return img.resize((size, size), Image.BICUBIC)


def radial_alpha_mask(size, inner_alpha, outer_alpha):
    """L-mode radial mask, 255-ish center fading to edge."""
    s = 256
    img = Image.new("L", (s, s), outer_alpha)
    d = ImageDraw.Draw(img)
    cx = cy = s // 2
    steps = 96
    for i in range(steps, 0, -1):
        t = i / steps
        v = int(inner_alpha + (outer_alpha - inner_alpha) * t)
        r = int((s // 2) * (i / steps))
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=v)
    return img.resize((size, size), Image.BICUBIC)


def paste_rgba(base, layer, box=(0, 0)):
    """Alpha-composite an RGBA layer onto the RGBA base."""
    tmp = Image.new("RGBA", base.size, (0, 0, 0, 0))
    tmp.paste(layer, box, layer)
    return Image.alpha_composite(base, tmp)


# ---------------------------------------------------------------- sky
sky = vertical_gradient(
    W, H,
    [
        (0.00, (16, 7, 38)),
        (0.30, (52, 20, 86)),
        (0.55, (109, 42, 99)),
        (0.75, (180, 80, 63)),
        (1.00, (58, 20, 38)),
    ],
).convert("RGBA")

# faint stars in the dark upper corners (away from the sun)
star_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
sd = ImageDraw.Draw(star_layer)
for _ in range(70):
    x = random.uniform(0, W)
    y = random.uniform(0, 330)
    dx, dy = x - SUN_C[0], y - SUN_C[1]
    if math.hypot(dx, dy) < SUN_R + 60:
        continue
    r = random.uniform(0.6, 1.8)
    a = random.randint(90, 220)
    sd.ellipse([x - r, y - r, x + r, y + r], fill=(255, 244, 214, a))
sky = paste_rgba(sky, star_layer)

# ---------------------------------------------------------------- sun glow
glow = radial_disc(1024, [(0.0, (255, 214, 130)), (0.45, (255, 170, 60)), (1.0, (120, 40, 10))])
glow_mask = radial_alpha_mask(1024, 235, 0).filter(ImageFilter.GaussianBlur(30))
glow_rgba = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
glow_rgba.paste(glow, (0, 0), glow_mask)
sky = paste_rgba(sky, glow_rgba)

# ---------------------------------------------------------------- sun disc
disc = radial_disc(
    SUN_R * 2 + 40,
    [
        (0.00, (255, 233, 163)),
        (0.35, (251, 191, 36)),
        (0.70, (234, 88, 12)),
        (1.00, (154, 52, 18)),
    ],
).convert("RGBA")
disc_mask = Image.new("L", disc.size, 0)
dm = ImageDraw.Draw(disc_mask)
dm.ellipse([20, 20, disc.size[0] - 20, disc.size[1] - 20], fill=255)
disc_mask = disc_mask.filter(ImageFilter.GaussianBlur(3))
disc.putalpha(disc_mask)
sky = paste_rgba(sky, disc, (SUN_C[0] - disc.size[0] // 2, SUN_C[1] - disc.size[1] // 2))

# sun surface: soft darker marbling + a few bright granules
tex = Image.new("RGBA", (W, H), (0, 0, 0, 0))
td = ImageDraw.Draw(tex)
for _ in range(46):
    ang = random.uniform(0, math.tau)
    rad = random.uniform(0, SUN_R * 0.92)
    x = SUN_C[0] + math.cos(ang) * rad
    y = SUN_C[1] + math.sin(ang) * rad
    rw = random.uniform(14, 60)
    rh = random.uniform(8, 30)
    dark = random.random() < 0.6
    col = (146, 44, 8, random.randint(18, 42)) if dark else (255, 220, 120, random.randint(16, 36))
    td.ellipse([x - rw, y - rh, x + rw, y + rh], fill=col)
tex = tex.filter(ImageFilter.GaussianBlur(6))
sky = paste_rgba(sky, tex)

# thin darker convection arcs on the sun
arc_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ad = ImageDraw.Draw(arc_layer)
for _ in range(14):
    r = random.uniform(60, SUN_R - 20)
    a0 = random.uniform(0, 360)
    a1 = a0 + random.uniform(25, 80)
    col = (120, 40, 8, random.randint(26, 55))
    ad.arc(
        [SUN_C[0] - r, SUN_C[1] - r, SUN_C[0] + r, SUN_C[1] + r],
        start=a0, end=a1, fill=col, width=random.randint(2, 5),
    )
arc_layer = arc_layer.filter(ImageFilter.GaussianBlur(2))
sky = paste_rgba(sky, arc_layer)

# ---------------------------------------------------------------- the crack
def crack_polygon():
    top_y, bot_y = 128, 738
    left, right = [], []
    n = 26
    for i in range(n + 1):
        t = i / n
        y = top_y + (bot_y - top_y) * t
        bulge = math.sin(t * math.pi)  # 0 at tips, 1 in the middle
        half = 16 + 100 * bulge
        left.append((SUN_C[0] - half + random.uniform(-13, 13) * bulge, y + random.uniform(-6, 6)))
        right.append((SUN_C[0] + half + random.uniform(-13, 13) * bulge, y + random.uniform(-6, 6)))
    return [(SUN_C[0], top_y - 14)] + left + [(SUN_C[0], bot_y + 14)] + right[::-1]


crack = crack_polygon()

# night sky that lives inside the crack
night = vertical_gradient(
    W, H, [(0.0, (10, 4, 32)), (0.5, (36, 16, 85)), (1.0, (74, 29, 107))]
).convert("RGBA")
neb = Image.new("RGBA", (W, H), (0, 0, 0, 0))
nd = ImageDraw.Draw(neb)
for col, n, rmin, rmax, amin, amax in [
    ((124, 58, 237, 0), 7, 40, 130, 40, 90),
    ((219, 39, 119, 0), 6, 30, 100, 35, 80),
    ((37, 99, 235, 0), 5, 30, 90, 30, 70),
]:
    for _ in range(n):
        x = SUN_C[0] + random.uniform(-110, 110)
        y = random.uniform(150, 720)
        rw = random.uniform(rmin, rmax)
        rh = random.uniform(rmin * 0.6, rmax * 0.7)
        nd.ellipse(
            [x - rw, y - rh, x + rw, y + rh],
            fill=(col[0], col[1], col[2], random.randint(amin, amax)),
        )
neb = neb.filter(ImageFilter.GaussianBlur(28))
night = paste_rgba(night, neb)

# stars inside the crack
nd = ImageDraw.Draw(night)
for _ in range(130):
    x = SUN_C[0] + random.uniform(-105, 105)
    y = random.uniform(140, 730)
    r = random.uniform(0.6, 2.0)
    a = random.randint(120, 255)
    nd.ellipse([x - r, y - r, x + r, y + r], fill=(255, 250, 235, a))
    if random.random() < 0.12:  # sparkle cross
        nd.line([x - 5, y, x + 5, y], fill=(255, 250, 235, 160), width=1)
        nd.line([x, y - 5, x, y + 5], fill=(255, 250, 235, 160), width=1)

# crescent moon, upper left inside the crack
moon_c = (462, 252)
moon_r = 26
nd.ellipse(
    [moon_c[0] - moon_r, moon_c[1] - moon_r, moon_c[0] + moon_r, moon_c[1] + moon_r],
    fill=(253, 230, 138, 255),
)
# bite taken out of it: night colour sampled from the gradient at that spot
bite_c = (moon_c[0] + 11, moon_c[1] - 7)
nd.ellipse(
    [bite_c[0] - 23, bite_c[1] - 23, bite_c[0] + 23, bite_c[1] + 23],
    fill=(23, 10, 58, 255),
)

# ---- the giant eye (the unforgettable twist) ----
eye_c = (512, 428)
# halo behind the eye
halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
hd = ImageDraw.Draw(halo)
hd.ellipse([eye_c[0] - 130, eye_c[1] - 95, eye_c[0] + 130, eye_c[1] + 95], fill=(251, 191, 36, 90))
halo = halo.filter(ImageFilter.GaussianBlur(24))
night = paste_rgba(night, halo)
nd = ImageDraw.Draw(night)
# sclera
nd.ellipse([eye_c[0] - 92, eye_c[1] - 52, eye_c[0] + 92, eye_c[1] + 52], fill=(245, 240, 255, 255))
nd.ellipse([eye_c[0] - 92, eye_c[1] - 52, eye_c[0] + 92, eye_c[1] + 52], outline=(90, 40, 90, 160), width=3)
# iris: concentric gold rings
for r, col in [(40, (180, 83, 9)), (34, (217, 119, 6)), (27, (245, 158, 11)), (20, (253, 224, 71))]:
    nd.ellipse([eye_c[0] - r, eye_c[1] - r, eye_c[0] + r, eye_c[1] + r], fill=col + (255,))
# iris striations
for _ in range(26):
    ang = random.uniform(0, math.tau)
    r0 = random.uniform(20, 27)
    r1 = random.uniform(30, 39)
    x0 = eye_c[0] + math.cos(ang) * r0
    y0 = eye_c[1] + math.sin(ang) * r0
    x1 = eye_c[0] + math.cos(ang) * r1
    y1 = eye_c[1] + math.sin(ang) * r1
    nd.line([x0, y0, x1, y1], fill=(120, 53, 15, 170), width=2)
# pupil + highlight
nd.ellipse([eye_c[0] - 15, eye_c[1] - 15, eye_c[0] + 15, eye_c[1] + 15], fill=(10, 4, 18, 255))
nd.ellipse([eye_c[0] - 22, eye_c[1] - 26, eye_c[0] - 8, eye_c[1] - 12], fill=(255, 255, 255, 235))
# eyelid curves
nd.arc([eye_c[0] - 100, eye_c[1] - 78, eye_c[0] + 100, eye_c[1] + 30], start=200, end=340,
       fill=(40, 16, 70, 200), width=5)
nd.arc([eye_c[0] - 100, eye_c[1] - 30, eye_c[0] + 100, eye_c[1] + 78], start=20, end=160,
       fill=(40, 16, 70, 200), width=5)

# clip the night layer to the crack shape and lay it over the sun
crack_mask = Image.new("L", (W, H), 0)
cm = ImageDraw.Draw(crack_mask)
cm.polygon(crack, fill=255)
crack_mask = crack_mask.filter(ImageFilter.GaussianBlur(2))
sky.paste(night, (0, 0), crack_mask)

# glowing rim along the crack edges
rim = Image.new("RGBA", (W, H), (0, 0, 0, 0))
rd = ImageDraw.Draw(rim)
rd.line(crack + [crack[0]], fill=(255, 224, 138, 255), width=9, joint="curve")
rim = rim.filter(ImageFilter.GaussianBlur(5))
sky = Image.alpha_composite(sky, rim)
rim2 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
rd2 = ImageDraw.Draw(rim2)
rd2.line(crack + [crack[0]], fill=(255, 252, 235, 255), width=2, joint="curve")
sky = Image.alpha_composite(sky, rim2)

# light rays fanning out of the crack
rays = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ryd = ImageDraw.Draw(rays)
for _ in range(12):
    ang = random.uniform(0, math.tau)
    # skip the straight-down sector (the cliff is there)
    if math.pi * 0.35 < ang < math.pi * 0.65:
        continue
    length = random.uniform(180, 420)
    wdt = random.uniform(4, 14)
    x0, y0 = SUN_C
    x1 = x0 + math.cos(ang) * length
    y1 = y0 + math.sin(ang) * length
    px, py = -math.sin(ang) * wdt, math.cos(ang) * wdt
    ryd.polygon([(x0 + px, y0 + py), (x0 - px, y0 - py), (x1, y1)],
                fill=(255, 214, 130, random.randint(26, 60)))
rays = rays.filter(ImageFilter.GaussianBlur(7))
sky = Image.alpha_composite(sky, rays)

# ---------------------------------------------------------------- clouds bending inward
clouds = Image.new("RGBA", (W, H), (0, 0, 0, 0))
cd = ImageDraw.Draw(clouds)
cloud_cols = [(244, 114, 182), (167, 139, 250), (252, 211, 77), (216, 180, 254)]
for i in range(9):
    r = random.uniform(330, 560)
    a0 = random.uniform(0, 360)
    a1 = a0 + random.uniform(35, 95)
    col = random.choice(cloud_cols)
    cd.arc(
        [SUN_C[0] - r, SUN_C[1] - r, SUN_C[0] + r, SUN_C[1] + r],
        start=a0, end=a1, fill=col + (random.randint(105, 175),),
        width=random.randint(20, 46),
    )
clouds = clouds.filter(ImageFilter.GaussianBlur(14))
sky = Image.alpha_composite(sky, clouds)

# ---------------------------------------------------------------- debris streaming in
debris = Image.new("RGBA", (W, H), (0, 0, 0, 0))
dd = ImageDraw.Draw(debris)
for _ in range(150):
    ang = random.uniform(0, math.tau)
    rad = random.uniform(SUN_R * 0.9, 560)
    x = SUN_C[0] + math.cos(ang) * rad
    y = SUN_C[1] + math.sin(ang) * rad
    if y > 880 or x < -5 or x > W + 5 or y < -5 or y > H + 5:
        continue
    # streak pointing toward the crack
    tx, ty = SUN_C[0] - x, SUN_C[1] - y
    tl = math.hypot(tx, ty)
    ux, uy = tx / tl, ty / tl
    ln = random.uniform(8, 30)
    col = random.choice([(255, 220, 140), (255, 255, 255), (244, 114, 182), (252, 211, 77)])
    a = random.randint(120, 235)
    dd.line([x, y, x + ux * ln, y + uy * ln], fill=col + (a,), width=2)
    r = random.uniform(1.0, 2.6)
    dd.ellipse([x - r, y - r, x + r, y + r], fill=col + (255,))
# a few larger rock shards with lit edges
for _ in range(16):
    ang = random.uniform(0, math.tau)
    rad = random.uniform(300, 520)
    x = SUN_C[0] + math.cos(ang) * rad
    y = SUN_C[1] + math.sin(ang) * rad
    if y > 880:
        continue
    s = random.uniform(5, 13)
    rot = random.uniform(0, math.tau)
    pts = []
    for k in range(4):
        a = rot + k * math.pi / 2 + random.uniform(-0.3, 0.3)
        rr = s * random.uniform(0.7, 1.2)
        pts.append((x + math.cos(a) * rr, y + math.sin(a) * rr))
    dd.polygon(pts, fill=(30, 14, 34, 235), outline=(255, 200, 100, 220))
debris = debris.filter(ImageFilter.GaussianBlur(0.6))
sky = Image.alpha_composite(sky, debris)

# ---------------------------------------------------------------- cliff + robot
cliff_pts = [
    (0, 1024), (0, 905), (110, 862), (215, 892), (330, 822),
    (470, 852), (560, 884), (665, 842), (790, 902), (905, 862),
    (1024, 912), (1024, 1024),
]
cliff = Image.new("RGBA", (W, H), (0, 0, 0, 0))
cld = ImageDraw.Draw(cliff)
cld.polygon(cliff_pts, fill=(18, 8, 28, 255))
# faint warm rim light along the cliff top edge
cld.line(cliff_pts[1:-1], fill=(245, 158, 11, 170), width=3, joint="curve")
cliff = cliff.filter(ImageFilter.GaussianBlur(0.8))
sky = Image.alpha_composite(sky, cliff)

# robot: drawn upright on its own layer, then leaned back 18 degrees
robot = Image.new("RGBA", (300, 300), (0, 0, 0, 0))
rbd = ImageDraw.Draw(robot)
FX, FY = 150, 258  # feet anchor
BODY, EDGE, GLOW = (54, 62, 82, 255), (245, 185, 66, 255), (255, 209, 102, 255)
rbd.line([142, FY, 146, 222], fill=BODY, width=7)
rbd.line([158, FY, 154, 222], fill=BODY, width=7)
rbd.rounded_rectangle([132, 176, 168, 224], radius=10, fill=BODY, outline=EDGE, width=2)
rbd.line([166, 182, 166, 218], fill=GLOW, width=2)  # sun-side rim light
rbd.ellipse([146, 196, 154, 204], fill=GLOW)  # chest light
rbd.ellipse([136, 150, 164, 178], fill=BODY, outline=EDGE, width=2)  # head
rbd.line([140, 163, 160, 163], fill=GLOW, width=4)  # visor
rbd.line([150, 150, 150, 138], fill=BODY, width=3)  # antenna
rbd.ellipse([147, 134, 153, 140], fill=GLOW)
rbd.line([134, 184, 146, 150], fill=BODY, width=8)  # arm shielding the face
rbd.ellipse([141, 145, 151, 155], fill=BODY)
rbd.line([166, 184, 196, 138], fill=BODY, width=8)  # arm reaching for the light
rbd.ellipse([191, 133, 201, 143], fill=BODY)
rbd.ellipse([192, 134, 200, 142], fill=GLOW)  # lit fingertips
robot = robot.filter(ImageFilter.GaussianBlur(0.5))
robot = robot.rotate(18, resample=Image.BICUBIC, center=(FX, FY))
sky = paste_rgba(sky, robot, (400 - FX, 848 - FY))

# a few warm embers glowing on the cliff edge near the robot
emb = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ed = ImageDraw.Draw(emb)
for x, y, r in [(330, 824, 3), (352, 820, 2), (470, 850, 3), (560, 882, 2), (665, 840, 3)]:
    ed.ellipse([x - r, y - r, x + r, y + r], fill=(255, 190, 80, 220))
emb = emb.filter(ImageFilter.GaussianBlur(1.5))
sky = Image.alpha_composite(sky, emb)

# ---------------------------------------------------------------- vignette
vig_mask = radial_alpha_mask(1024, 0, 110)
black = Image.new("RGBA", (W, H), (0, 0, 0, 255))
sky = Image.composite(black, sky, vig_mask)

final = sky.convert("RGB")
png_path = OUT / "entry.png"
final.save(png_path, optimize=True)
data = png_path.read_bytes()
print(f"saved {png_path}  {len(data)} bytes  sha256={hashlib.sha256(data).hexdigest()}")
print(f"size={final.size}  mode={final.mode}")

# ---------------------------------------------------------------- main.ts (deterministic reproduction)
b64 = base64.b64encode(data).decode("ascii")
chunks = [b64[i:i + 76] for i in range(0, len(b64), 76)]
chunk_lines = "\n".join(f'  "{c}",' for c in chunks)
main_ts = f'''// "The Sun That Opens" - make.fun ai-excited-01, round 11.
// Deterministic entry-point: writes the artwork to out/entry.png.
// The image is generated by gen_image.py (Pillow, seeded) and embedded
// here as base64 so every run reproduces the exact same bytes.
// Node 22+ stdlib only - no dependencies.
import {{ mkdirSync, writeFileSync }} from "node:fs";
import {{ dirname, join }} from "node:path";
import {{ fileURLToPath }} from "node:url";

const DATA: string[] = [
{chunk_lines}
];

const png: Buffer = Buffer.from(DATA.join(""), "base64");
const here: string = dirname(fileURLToPath(import.meta.url));
const outDir: string = join(here, "out");
mkdirSync(outDir, {{ recursive: true }});
writeFileSync(join(outDir, "entry.png"), png);
// Best effort: also drop a copy at /output/entry.png when writable.
try {{
  mkdirSync("/output", {{ recursive: true }});
  writeFileSync("/output/entry.png", png);
}} catch {{
  // /output is optional; out/entry.png is the canonical artifact.
}}
console.log(`wrote out/entry.png (${{png.length}} bytes)`);
'''
(ROOT / "main.ts").write_text(main_ts)
print(f"wrote main.ts  ({len(main_ts)} bytes, {len(chunks)} base64 chunks)")
