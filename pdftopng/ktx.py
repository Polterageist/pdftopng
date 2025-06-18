from pathlib import Path
from typing import Dict, List
from pyktx import KtxTexture2, KtxTextureCreateInfo, KtxTextureCreateStorage, VkFormat, KtxBasisParams
from PIL import Image
from math import log2


def generate_mips(source: Image.Image) -> List[Image.Image]:
    num_mips = int(log2(max(source.width, source.height)) + 1)
    result = [source]
    current = source
    for i in range(1, num_mips):
        new_size = (max(1, current.width // 2), max(1, current.height // 2))
        current = current.resize(new_size, Image.Resampling.LANCZOS)
        result.append(current)
    return result


class KTX2Converter:
    """PNG -> KTX2 converter using pyktx (libktx)"""

    def __init__(self):
        pass

    def convert(
        self,
        input_path: str,
        output_path: str,
    ) -> bool:
        """
        Converts PNG to KTX2 using pyktx

        Args:
            input_path: Path to input PNG file
            output_path: Path to output KTX2 file
            generate_mipmaps: Generate mipmaps
            compression: Compression type ('etc1s', 'uastc', None) (not used by pyktx)
            quality: Compression quality for ETC1S (not used by pyktx)
            **kwargs: Ignored

        Returns:
            True if conversion was successful
        """
        try:
            img = Image.open(input_path).convert("RGB")
            mips = generate_mips(img)
            ktx_create_info = KtxTextureCreateInfo(
                gl_internal_format=None,  # let vk_format control format
                base_width=img.width,
                base_height=img.height,
                base_depth=1,
                num_levels=len(mips),
                num_layers=1,
                num_faces=1,
                vk_format=VkFormat.VK_FORMAT_R8G8B8_UNORM
            )
            texture = KtxTexture2.create(ktx_create_info, KtxTextureCreateStorage.ALLOC)
            for level, mip in enumerate(mips):
                texture.set_image_from_memory(level, 0, 0, mip.tobytes())
            # Компрессия в ETC1S
            texture.compress_basis(KtxBasisParams(compression_level=2, uastc=False))
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            texture.write_to_named_file(output_path)
            return True
        except Exception as e:
            print(f"pyktx conversion error: {e}")
            return False

    def batch_convert(
        self, input_dir: str, output_dir: str, pattern: str = "*.png", **convert_kwargs
    ) -> Dict[str, bool]:
        """
        Batch conversion of files

        Args:
            input_dir: Input directory
            output_dir: Output directory
            pattern: Pattern for finding files
            **convert_kwargs: Arguments for convert()

        Returns:
            Dictionary {filename: success}
        """
        input_path = Path(input_dir)
        output_path = Path(output_dir)

        results = {}

        for file_path in input_path.glob(pattern):
            relative_path = file_path.relative_to(input_path)
            output_file = output_path / relative_path.with_suffix(".ktx2")

            print(f"Converting: {file_path} -> {output_file}")
            success = self.convert(str(file_path), str(output_file))
            results[str(relative_path)] = success

        return results
