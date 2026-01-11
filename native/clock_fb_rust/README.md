# Rust Framebuffer Clock Renderer

A tiny Rust daemon that memory-maps `/dev/fb0` and renders the time/date with a glyph atlas for high performance on Raspberry Pi (RGB565). It listens on stdin for simple commands and updates the framebuffer without full-frame copies.

## Build

Install Rust toolchain inside your Balena container or base image:

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source $HOME/.cargo/env
cd /app/native/clock_fb_rust
cargo build --release
```

The binary will be at `target/release/clock_fb_rust`.

## Run

From your app root:

```bash
/app/native/clock_fb_rust/target/release/clock_fb_rust
```

It reads commands from stdin:
- `TIME <string>`
- `DATE <string>`
- `BRIGHT <0.0-1.0>`
- `COLOR #RRGGBB`
- `SHIFT <x> <y>`
- `QUIT`

## Configuration

- Env `FONT_PATH` (default: `/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf`)
- Env `TIME_SIZE` (default: 280)
- Env `DATE_SIZE` (default: 90)
- Env `FB_DEVICE` (default: `/dev/fb0`)

## Protocol example

```bash
echo "BRIGHT 0.8" | ./clock_fb_rust
echo "COLOR #00FF00" | ./clock_fb_rust
echo "TIME 10:00:00 PM" | ./clock_fb_rust
echo "DATE Sat, Jan 10" | ./clock_fb_rust
```

## Notes
- Uses RGB565 with symmetric padding and clamps within margins.
- Aligns internal updates to second boundaries; applies pixel shift only at minute boundaries.
- Future: add weather/status rendering.
