use fontdue::layout::{CoordinateSystem, Layout, LayoutSettings, TextStyle};
use fontdue::Font;
use memmap2::{MmapMut, MmapOptions};
use std::fs::File;
use std::io::{self, BufRead};
use std::str::FromStr;

#[derive(Clone, Copy)]
struct ColorRgb565(u16);

fn rgb_to_rgb565(r: u8, g: u8, b: u8) -> ColorRgb565 {
    let r5 = (r as u16 >> 3) & 0x1f;
    let g6 = (g as u16 >> 2) & 0x3f;
    let b5 = (b as u16 >> 3) & 0x1f;
    ColorRgb565((r5 << 11) | (g6 << 5) | b5)
}

fn parse_hex_color(s: &str) -> (u8, u8, u8) {
    let hex = s.trim_start_matches('#');
    if hex.len() == 6 {
        let r = u8::from_str_radix(&hex[0..2], 16).unwrap_or(0);
        let g = u8::from_str_radix(&hex[2..4], 16).unwrap_or(0);
        let b = u8::from_str_radix(&hex[4..6], 16).unwrap_or(0);
        (r, g, b)
    } else {
        (0, 255, 0)
    }
}

fn read_fb_size() -> (usize, usize) {
    if let Ok(s) = std::fs::read_to_string("/sys/class/graphics/fb0/virtual_size") {
        let parts: Vec<&str> = s.trim().split(',').collect();
        if parts.len() == 2 {
            let w = parts[0].parse::<usize>().unwrap_or(1920);
            let h = parts[1].parse::<usize>().unwrap_or(1200);
            return (w, h);
        }
    }
    (1920, 1200)
}

struct Renderer {
    fb: MmapMut,
    fb_w: usize,
    fb_h: usize,
    stride: usize,
    back: Vec<u8>,
    color: (u8, u8, u8),
    bright: f32,
    time_size: f32,
    date_size: f32,
    font: Font,
    shift_x: isize,
    shift_y: isize,
    margin: usize,
    last_time_rect: Option<(usize, usize, usize, usize)>,
    last_date_rect: Option<(usize, usize, usize, usize)>,
    time_text: String,
    date_text: String,
}

impl Renderer {
    fn new() -> io::Result<Self> {
        let fb_path = std::env::var("FB_DEVICE").unwrap_or("/dev/fb0".to_string());
        let (fb_w, fb_h) = read_fb_size();
        let file = File::options().read(true).write(true).open(&fb_path)?;
        // SAFETY: map framebuffer with explicit length
        let fb_len = fb_w * fb_h * 2; // RGB565
        let fb = unsafe { MmapOptions::new().len(fb_len).map_mut(&file)? };
        let font_path = std::env::var("FONT_PATH").unwrap_or("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf".to_string());
        let font_bytes = std::fs::read(&font_path).expect("Font file not found");
        let font = Font::from_bytes(font_bytes, fontdue::FontSettings::default()).expect("Invalid font");
        let mut r = Self {
            fb,
            fb_w,
            fb_h,
            stride: fb_w * 2,
            back: vec![0u8; fb_len],
            color: parse_hex_color(&std::env::var("COLOR").unwrap_or("#00FF00".to_string())),
            bright: 1.0,
            time_size: std::env::var("TIME_SIZE").ok().and_then(|s| f32::from_str(&s).ok()).unwrap_or(280.0),
            date_size: std::env::var("DATE_SIZE").ok().and_then(|s| f32::from_str(&s).ok()).unwrap_or(90.0),
            font,
            shift_x: 0,
            shift_y: 0,
            margin: 30,
            last_time_rect: None,
            last_date_rect: None,
            time_text: String::new(),
            date_text: String::new(),
        };
        // Clear framebuffer on startup to remove boot background remnants
        r.clear_rect(0, 0, r.fb_w, r.fb_h);
        Ok(r)
    }

    fn clear_rect(&mut self, x: usize, y: usize, w: usize, h: usize) {
        let x2 = x.saturating_add(w).min(self.fb_w);
        let y2 = y.saturating_add(h).min(self.fb_h);
        for row in y..y2 {
            let off = row * self.stride + x * 2;
            for col in 0..(x2 - x) {
                let idx = off + col * 2;
                self.fb[idx] = 0;
                self.fb[idx + 1] = 0;
            }
        }
    }

    fn clear_rect_diff(&mut self, old: (usize, usize, usize, usize), new: (usize, usize, usize, usize)) {
        let (ox, oy, ow, oh) = old;
        let (nx, ny, nw, nh) = new;
        // Intersection
        let ix1 = ox.max(nx);
        let iy1 = oy.max(ny);
        let ix2 = (ox + ow).min(nx + nw);
        let iy2 = (oy + oh).min(ny + nh);
        let has_intersection = ix2 > ix1 && iy2 > iy1;
        if !has_intersection {
            // No overlap, clear entire old rect
            self.clear_rect(ox, oy, ow, oh);
            return;
        }
        // Clear left band
        if ix1 > ox {
            self.clear_rect(ox, oy, ix1 - ox, oh);
        }
        // Clear right band
        if ix2 < ox + ow {
            self.clear_rect(ix2, oy, (ox + ow) - ix2, oh);
        }
        // Clear top band within intersection width
        if iy1 > oy {
            self.clear_rect(ix1, oy, ix2 - ix1, iy1 - oy);
        }
        // Clear bottom band within intersection width
        if iy2 < oy + oh {
            self.clear_rect(ix1, iy2, ix2 - ix1, (oy + oh) - iy2);
        }
    }

    fn padding_for_size(size: f32) -> (usize, usize) {
        // Scale padding with text size to avoid edge clipping at large sizes
        let pad_lr = ((size / 12.0).ceil() as usize).max(16);
        let pad_tb = ((size / 28.0).ceil() as usize).max(6);
        (pad_lr, pad_tb)
    }

    fn compute_layout_and_bounds(&self, text: &str, size: f32) -> (Layout, usize, usize, f32, f32) {
        let mut layout = Layout::new(CoordinateSystem::PositiveYDown);
        layout.reset(&LayoutSettings { ..LayoutSettings::default() });
        layout.append(&[&self.font], &TextStyle::new(text, size, 0));

        let glyphs = layout.glyphs();
        if glyphs.is_empty() {
            return (layout, 0, 0, 0.0, 0.0);
        }
        let mut min_x = f32::MAX;
        let mut min_y = f32::MAX;
        let mut max_x = f32::MIN;
        let mut max_y = f32::MIN;

        for glyph in glyphs {
            let (metrics, _) = self.font.rasterize_config(glyph.key);
            let gx = glyph.x + metrics.xmin as f32;
            let gy = glyph.y + metrics.ymin as f32;
            let gx2 = gx + metrics.width as f32;
            let gy2 = gy + metrics.height as f32;
            min_x = min_x.min(gx);
            min_y = min_y.min(gy);
            max_x = max_x.max(gx2);
            max_y = max_y.max(gy2);
        }
        let text_w = (max_x - min_x).ceil() as usize;
        let text_h = (max_y - min_y).ceil() as usize;
        (layout, text_w, text_h, min_x, min_y)
    }

    fn compute_pos(&self, text_w: usize, text_h: usize, size: f32, y_center_offset: isize, min_top_y: Option<usize>) -> (usize, usize, usize, usize, usize, usize) {
        let (pad_lr, pad_tb) = Self::padding_for_size(size);
        let canvas_w = text_w + pad_lr * 2;
        let canvas_h = text_h + pad_tb * 2;
        let center_x = (self.fb_w as isize / 2) + self.shift_x;
        let center_y = (self.fb_h as isize / 2) + self.shift_y + y_center_offset;
        let desired_x = center_x - (canvas_w as isize / 2);
        let mut desired_y = center_y - (canvas_h as isize / 2);
        if let Some(min_y) = min_top_y {
            let min_y_isize = min_y as isize;
            if desired_y < min_y_isize { desired_y = min_y_isize; }
        }
        let mut x = desired_x.max(self.margin as isize) as usize;
        let mut y = desired_y.max(self.margin as isize) as usize;
        if x + canvas_w + self.margin > self.fb_w { x = self.fb_w.saturating_sub(canvas_w + self.margin); }
        if y + canvas_h + self.margin > self.fb_h { y = self.fb_h.saturating_sub(canvas_h + self.margin); }
        (x, y, canvas_w, canvas_h, pad_lr, pad_tb)
    }

    fn draw_layout_to(&self, dest: &mut [u8], layout: &Layout, x: usize, y: usize, pad_lr: usize, pad_tb: usize) {
        // Color with brightness
        let (cr, cg, cb) = self.color;
        let r = (cr as f32 * self.bright).min(255.0) as u8;
        let g = (cg as f32 * self.bright).min(255.0) as u8;
        let b = (cb as f32 * self.bright).min(255.0) as u8;
        // Rasterize each glyph at layout positions with simple alpha blend on black
        for glyph in layout.glyphs() {
            let (metrics, bitmap) = self.font.rasterize_config(glyph.key);
            let gx = x as isize + pad_lr as isize + glyph.x as isize + metrics.xmin as isize;
            let gy = y as isize + pad_tb as isize + glyph.y as isize + metrics.ymin as isize;
            let gw = metrics.width as isize;
            let gh = metrics.height as isize;
            for row in 0..gh {
                let dest_y = gy + row;
                if dest_y < 0 || dest_y >= self.fb_h as isize { continue; }
                let off = dest_y as usize * self.stride + (gx.max(0) as usize) * 2;
                for col in 0..gw {
                    let dest_x = gx + col;
                    if dest_x < 0 || dest_x >= self.fb_w as isize { continue; }
                    let cov = bitmap[(row * gw + col) as usize];
                    if cov > 0 {
                        // Scale color by coverage (background assumed black)
                        let covf = cov as f32 / 255.0;
                        let sr = (r as f32 * covf) as u8;
                        let sg = (g as f32 * covf) as u8;
                        let sb = (b as f32 * covf) as u8;
                        let c565 = rgb_to_rgb565(sr, sg, sb).0;
                        let idx = off + (col as usize) * 2;
                        dest[idx] = (c565 & 0xFF) as u8;
                        dest[idx + 1] = (c565 >> 8) as u8;
                    }
                }
            }
        }
    }
    
    fn render_frame(&mut self) {
        // Clear backbuffer to black
        for b in &mut self.back { *b = 0; }
        // Render time if present
        let mut min_top_for_date: Option<usize> = None;
        if !self.time_text.is_empty() {
            let (layout, tw, th, _minx, _miny) = self.compute_layout_and_bounds(&self.time_text, self.time_size);
            let (x, y, w, h, pad_lr, pad_tb) = self.compute_pos(tw, th, self.time_size, -100, None);
            self.draw_layout_to(&mut self.back, &layout, x, y, pad_lr, pad_tb);
            self.last_time_rect = Some((x, y, w, h));
            min_top_for_date = Some(y + h + 8);
        }
        // Render date if present
        if !self.date_text.is_empty() {
            let (layout, tw, th, _minx, _miny) = self.compute_layout_and_bounds(&self.date_text, self.date_size);
            let (x, y, w, h, pad_lr, pad_tb) = self.compute_pos(tw, th, self.date_size, 140, min_top_for_date);
            self.draw_layout_to(&mut self.back, &layout, x, y, pad_lr, pad_tb);
            self.last_date_rect = Some((x, y, w, h));
        }
        // Blit backbuffer to framebuffer atomically
        self.fb.copy_from_slice(&self.back);
    }

    fn handle_line(&mut self, line: &str) {
        let mut parts = line.trim().split_whitespace();
        if let Some(cmd) = parts.next() {
            match cmd {
                "TIME" => {
                    let rest = line.trim()[4..].trim();
                    self.time_text = rest.to_string();
                    self.render_frame();
                }
                "DATE" => {
                    let rest = line.trim()[4..].trim();
                    self.date_text = rest.to_string();
                    self.render_frame();
                }
                "BRIGHT" => {
                    if let Some(val) = parts.next() { self.bright = f32::from_str(val).unwrap_or(1.0).clamp(0.0, 1.0); }
                    self.render_frame();
                }
                "COLOR" => {
                    if let Some(hex) = parts.next() { self.color = parse_hex_color(hex); }
                    self.render_frame();
                }
                "SHIFT" => {
                    if let (Some(xs), Some(ys)) = (parts.next(), parts.next()) {
                        self.shift_x = isize::from_str(xs).unwrap_or(0).clamp(-10, 10);
                        self.shift_y = isize::from_str(ys).unwrap_or(0).clamp(-10, 10);
                    }
                    self.render_frame();
                }
                "QUIT" => {
                    std::process::exit(0);
                }
                _ => {}
            }
        }
    }
}

fn main() -> io::Result<()> {
    let mut renderer = Renderer::new()?;
    let stdin = io::stdin();
    for line in stdin.lock().lines() {
        if let Ok(line) = line { renderer.handle_line(&line); }
    }
    Ok(())
}
