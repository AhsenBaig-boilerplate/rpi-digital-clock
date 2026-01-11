use fontdue::layout::{CoordinateSystem, Layout, LayoutSettings, TextStyle};
use fontdue::Font;
use memmap2::MmapMut;
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
}

impl Renderer {
    fn new() -> io::Result<Self> {
        let fb_path = std::env::var("FB_DEVICE").unwrap_or("/dev/fb0".to_string());
        let (fb_w, fb_h) = read_fb_size();
        let file = File::options().read(true).write(true).open(&fb_path)?;
        // SAFETY: map framebuffer size
        let fb = unsafe { MmapMut::map_mut(&file)? };
        let font_path = std::env::var("FONT_PATH").unwrap_or("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf".to_string());
        let font_bytes = std::fs::read(&font_path).expect("Font file not found");
        let font = Font::from_bytes(font_bytes, fontdue::FontSettings::default()).expect("Invalid font");
        Ok(Self {
            fb,
            fb_w,
            fb_h,
            stride: fb_w * 2,
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
        })
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

    fn draw_text_centered(&mut self, text: &str, size: f32, y_center_offset: isize) -> (usize, usize, usize, usize) {
        // Layout text
        let mut layout = Layout::new(CoordinateSystem::PositiveYDown);
        layout.reset(&LayoutSettings { ..LayoutSettings::default() });
        layout.append(&[&self.font], &TextStyle::new(text, size, 0));
        
        // Calculate bounding box from glyphs
        let glyphs = layout.glyphs();
        if glyphs.is_empty() {
            return (0, 0, 0, 0);
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
        let pad_lr = 16usize;
        let pad_tb = 6usize;
        let canvas_w = text_w + pad_lr * 2;
        let canvas_h = text_h + pad_tb * 2;
        let center_x = (self.fb_w as isize / 2) + self.shift_x;
        let center_y = (self.fb_h as isize / 2) + self.shift_y + y_center_offset;
        let desired_x = center_x - (canvas_w as isize / 2);
        let desired_y = center_y - (canvas_h as isize / 2);
        let mut x = desired_x.max(self.margin as isize) as usize;
        let mut y = desired_y.max(self.margin as isize) as usize;
        if x + canvas_w + self.margin > self.fb_w { x = self.fb_w.saturating_sub(canvas_w + self.margin); }
        if y + canvas_h + self.margin > self.fb_h { y = self.fb_h.saturating_sub(canvas_h + self.margin); }
        // Color with brightness
        let (cr, cg, cb) = self.color;
        let r = (cr as f32 * self.bright).min(255.0) as u8;
        let g = (cg as f32 * self.bright).min(255.0) as u8;
        let b = (cb as f32 * self.bright).min(255.0) as u8;
        let color565 = rgb_to_rgb565(r, g, b).0;
        // Rasterize each glyph at layout positions
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
                    // Simple threshold blend (monochrome)
                    if cov > 128 {
                        let idx = off + (col as usize) * 2;
                        self.fb[idx] = (color565 & 0xFF) as u8;
                        self.fb[idx + 1] = (color565 >> 8) as u8;
                    }
                }
            }
        }
        (x, y, canvas_w, canvas_h)
    }

    fn handle_line(&mut self, line: &str) {
        let mut parts = line.trim().split_whitespace();
        if let Some(cmd) = parts.next() {
            match cmd {
                "TIME" => {
                    let rest = line.trim()[4..].trim();
                    if let Some((x, y, w, h)) = self.last_time_rect {
                        self.clear_rect(x, y, w, h);
                    }
                    let rect = self.draw_text_centered(rest, self.time_size, -60);
                    self.last_time_rect = Some(rect);
                }
                "DATE" => {
                    let rest = line.trim()[4..].trim();
                    if let Some((x, y, w, h)) = self.last_date_rect {
                        self.clear_rect(x, y, w, h);
                    }
                    let rect = self.draw_text_centered(rest, self.date_size, 100);
                    self.last_date_rect = Some(rect);
                }
                "BRIGHT" => {
                    if let Some(val) = parts.next() { self.bright = f32::from_str(val).unwrap_or(1.0).clamp(0.0, 1.0); }
                }
                "COLOR" => {
                    if let Some(hex) = parts.next() { self.color = parse_hex_color(hex); }
                }
                "SHIFT" => {
                    if let (Some(xs), Some(ys)) = (parts.next(), parts.next()) {
                        self.shift_x = isize::from_str(xs).unwrap_or(0).clamp(-10, 10);
                        self.shift_y = isize::from_str(ys).unwrap_or(0).clamp(-10, 10);
                    }
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
