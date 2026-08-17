"""去除 v1 头像右下角平台水印。

策略：水印区域位于右下角约 22% 宽 × 8% 高。背景是浅灰径向渐变，水平方向色差
明显，垂直方向色差较小。逐像素取该列上方紧邻 1 行的像素值作为填充——
可修复水平渐变，避免单色填充留色块。
"""

from PIL import Image
from pathlib import Path

ROOT = Path("/Users/shaqsmacair/my-codes/OctopusMate/avatars")
src = ROOT / "octopus-mate-v1-geometric.png"
dst = ROOT / "octopus-mate.png"  # 直接覆盖 plugin.json 引用


def remove_watermark(src: Path, dst: Path) -> None:
    img = Image.open(src).convert("RGB")
    w, h = img.size

    # 水印区域 bbox：右下角，目测约占 22% 宽 × 8% 高
    wx0 = int(w * 0.76)
    wy0 = int(h * 0.90)

    pixels = img.load()

    # 逐像素：用该列上方紧邻 2 行的同列像素值填充（水印上方 2 行的像素未受水印污染）
    for y in range(wy0, h):
        for x in range(wx0, w):
            ref = pixels[x, wy0 - 2]
            pixels[x, y] = ref

    img.save(dst, "PNG")


if __name__ == "__main__":
    remove_watermark(src, dst)
    print(f"水印去除完成 → {dst}")
