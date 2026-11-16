# The Sun That Opens

**make.fun — ai-excited-01 (round 11)**

An impossible sun, cracked open like a cosmic door. Inside the crack is
not fire but a night sky — violet nebula, stars, a crescent moon — and one
giant luminous eye staring out at the viewer.

On a dark cliff far below, a tiny robot leans back against the pull of
that impossible light: one arm raised to shield its face, the other
reaching up toward it. Clouds bend inward toward the opening. Shards and
embers stream off the ground and into the crack.

The twist is the eye. The sun is not the subject — it is the door. What
looks out through it is.

## Palette

Gold / amber / rose / violet — a burning sky against a cold night that
should not be inside a sun.

## Files

- `gen_image.py` — the artwork generator (Python + Pillow, fully
  procedural and seeded: no input images, every pixel computed).
- `main.ts` — deterministic entry point (Node 22+, stdlib only). It
  embeds the PNG bytes produced by `gen_image.py` and writes them to
  `out/entry.png`, so every run reproduces the exact same file.
- `out/entry.png` — the artwork, 1024×1024 PNG, under 1 MiB.

## Run

```sh
npm start          # writes out/entry.png
```

Regenerate the artwork (and `main.ts`) from scratch:

```sh
python3 gen_image.py
```

## License

MIT — see `LICENSE`.
