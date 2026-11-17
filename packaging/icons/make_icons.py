from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUTPUT = Path(__file__).parent
SIZE = 256


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def main() -> None:
    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((8, 8, 247, 247), radius=44, fill=(23, 82, 160, 255))
    draw.rounded_rectangle((44, 34, 212, 222), radius=12, fill=(255, 255, 255, 245))
    draw.rectangle((72, 70, 184, 80), fill=(23, 82, 160, 255))
    draw.rectangle((72, 104, 184, 112), fill=(96, 132, 180, 255))
    draw.rectangle((72, 136, 152, 144), fill=(96, 132, 180, 255))
    draw.polygon([(196, 196), (222, 170), (222, 196)], fill=(23, 82, 160, 255))
    font = load_font(34)
    draw.text((72, 160), "H2D", font=font, fill=(23, 82, 160, 255))
    image.save(OUTPUT / "icon.png")
    image.save(OUTPUT / "icon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])


if __name__ == "__main__":
    main()
