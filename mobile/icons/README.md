# PWA Icons

Place your app icons here:

- `icon-192.png` - 192x192 pixels
- `icon-512.png` - 512x512 pixels

## Generate Icons

You can generate PWA icons from a single source image using tools like:

- [PWA Asset Generator](https://github.com/onderceylan/pwa-asset-generator)
- [RealFaviconGenerator](https://realfavicongenerator.net/)

## Quick Generation

Using ImageMagick:
```bash
# From a source SVG or PNG
convert source.png -resize 192x192 icon-192.png
convert source.png -resize 512x512 icon-512.png
```

## Icon Design Guidelines

- Use simple, recognizable symbols (e.g., leaf, microscope, plant)
- High contrast for visibility
- Square aspect ratio
- No text (too small to read)
- Consider Apple's icon guidelines for best iOS appearance
