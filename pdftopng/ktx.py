from pathlib import Path
from typing import Dict, List
from pyktx import KtxTexture2, KtxTextureCreateInfo, KtxTextureCreateStorage, VkFormat, KtxBasisParams
from PIL import Image
from math import log2
import concurrent.futures
import multiprocessing


def generate_mips(source: Image.Image) -> List[Image.Image]:
    num_mips = int(log2(max(source.width, source.height)) + 1)
    result = [source]
    current = source
    for i in range(1, num_mips):
        new_size = (max(1, current.width // 2), max(1, current.height // 2))
        current = current.resize(new_size, Image.Resampling.LANCZOS)
        result.append(current)
    return result


def convert_one_file(args):
    cls, file_path, input_dir, output_dir, convert_kwargs = args
    relative_path = file_path.relative_to(input_dir)
    output_file = output_dir / relative_path.with_suffix(".ktx2")
    print(f"[START] Converting: {file_path} -> {output_file}")
    converter = cls()
    success = converter.convert(str(file_path), str(output_file), **convert_kwargs)
    if success:
        print(f"[OK]    {file_path} -> {output_file}")
    else:
        print(f"[FAIL]  {file_path} -> {output_file}")
    return str(relative_path), success


class KTX2Converter:
    """PNG -> KTX2 converter using pyktx (libktx)"""

    def __init__(self):
        pass

    def convert(
        self,
        input_path: str,
        output_path: str,
        **kwargs
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
        Batch conversion of files (parallelized, safe for multiprocessing)
        """
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        files = list(input_path.glob(pattern))
        results = {}
        num_workers = multiprocessing.cpu_count()
        args_list = [
            (self.__class__, file_path, input_path, output_path, convert_kwargs)
            for file_path in files
        ]
        print(f"[BATCH] Starting batch conversion: {len(files)} files, {num_workers} workers")
        with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
            for rel, success in executor.map(convert_one_file, args_list):
                results[rel] = success
        print(f"[BATCH] Done. Success: {sum(results.values())}, Fail: {len(results)-sum(results.values())}")
        return results
