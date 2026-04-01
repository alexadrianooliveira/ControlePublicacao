"""Gera o ícone do File Selector - pasta com seta de exportação."""
from PIL import Image, ImageDraw

def create_icon(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    p = size / 256

    # Sombra da pasta
    so = int(3 * p)
    draw.rounded_rectangle(
        [int(10*p)+so, int(70*p)+so, int(230*p)+so, int(210*p)+so],
        radius=int(12*p), fill=(0, 0, 0, 40)
    )
    # Corpo da pasta (trás)
    draw.rounded_rectangle(
        [int(10*p), int(70*p), int(230*p), int(210*p)],
        radius=int(12*p), fill=(52, 152, 219)
    )
    # Aba da pasta
    draw.rounded_rectangle(
        [int(10*p), int(48*p), int(110*p), int(85*p)],
        radius=int(8*p), fill=(41, 128, 185)
    )
    # Frente da pasta
    draw.rounded_rectangle(
        [int(10*p), int(90*p), int(230*p), int(210*p)],
        radius=int(12*p), fill=(93, 173, 226)
    )
    # Linhas (arquivos)
    for i, y in enumerate([120, 142, 164]):
        draw.rounded_rectangle(
            [int(30*p), int(y*p), int(140*p), int((y+12)*p)],
            radius=int(3*p), fill=(255, 255, 255, 200 - i*30)
        )
    # Círculo verde
    cx, cy, r = int(185*p), int(185*p), int(52*p)
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(46, 204, 113))
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=(39, 174, 96), width=max(1, int(3*p)))
    # Seta
    aw = int(10*p)
    hw = int(20*p)
    top = cy - int(28*p)
    bot = cy + int(22*p)
    draw.rectangle([cx-aw, top+int(18*p), cx+aw, bot], fill=(255, 255, 255))
    draw.polygon([(cx, top), (cx-hw, top+int(22*p)), (cx+hw, top+int(22*p))], fill=(255, 255, 255))

    return img

# Gerar cada tamanho individualmente (não redimensionado)
ico_sizes = [16, 24, 32, 48, 64, 128, 256]
images = [create_icon(sz) for sz in ico_sizes]

# Salvar .ico com todos os tamanhos
images[-1].save(
    "file_selector.ico",
    format="ICO",
    append_images=images[:-1],
    sizes=[(sz, sz) for sz in ico_sizes]
)

# Verificar
from PIL import Image as Im
ico = Im.open("file_selector.ico")
print(f"ICO gerado: {ico.info.get('sizes', 'N/A')}")
print(f"Arquivo: {__import__('os').path.getsize('file_selector.ico')} bytes")
