import os
import re
import zlib
import gzip
import logging
from typing import Generator, Tuple, Dict, Any, Optional
from app.scanner.nbt_reader import parse_nbt

logger = logging.getLogger(__name__)

MCA_FILENAME_PATTERN = re.compile(r"^r\.(-?\d+)\.(-?\d+)\.mca$")

def parse_region_coords(filename: str) -> Optional[Tuple[int, int]]:
    """Extract (region_x, region_z) from filename like 'r.-1.2.mca'."""
    match = MCA_FILENAME_PATTERN.match(filename)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None

def chunk_coords_to_block_coords(chunk_x: int, chunk_z: int, local_x: int = 0, local_z: int = 0) -> Tuple[int, int]:
    """Convert chunk coordinates to block coordinates."""
    return (chunk_x * 16) + local_x, (chunk_z * 16) + local_z

def block_coords_to_chunk_coords(block_x: int, block_z: int) -> Tuple[int, int]:
    """Convert block coordinates to chunk coordinates."""
    return block_x >> 4, block_z >> 4

def chunk_coords_to_region_coords(chunk_x: int, chunk_z: int) -> Tuple[int, int]:
    """Convert chunk coordinates to region coordinates."""
    return chunk_x >> 5, chunk_z >> 5

class MCAReader:
    """Read Minecraft Java Anvil (.mca) region files safely in read-only mode."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        coords = parse_region_coords(self.filename)
        if coords is None:
            raise ValueError(f"Invalid MCA filename format: {self.filename}")
        self.region_x, self.region_z = coords

    def read_chunks(self) -> Generator[Tuple[int, int, Dict[str, Any]], None, None]:
        """
        Yield (chunk_x, chunk_z, nbt_data) for all valid chunks in this region.
        Handles corrupt chunks gracefully without aborting the scan.
        """
        if not os.path.exists(self.filepath):
            logger.warning(f"MCA file not found: {self.filepath}")
            return

        file_size = os.path.getsize(self.filepath)
        if file_size < 8192:
            # Region file must be at least 8KB (header 4KB + timestamp 4KB)
            logger.warning(f"Truncated or empty MCA file: {self.filepath} ({file_size} bytes)")
            return

        try:
            with open(self.filepath, "rb") as f:
                header = f.read(4096)
                if len(header) < 4096:
                    return

                for i in range(1024):
                    entry = header[i * 4 : (i + 1) * 4]
                    offset_sectors = int.from_bytes(entry[:3], "big")
                    sector_count = entry[3]

                    if offset_sectors == 0 or sector_count == 0:
                        continue

                    local_chunk_x = i % 32
                    local_chunk_z = i // 32
                    chunk_x = (self.region_x * 32) + local_chunk_x
                    chunk_z = (self.region_z * 32) + local_chunk_z

                    byte_offset = offset_sectors * 4096
                    if byte_offset + 5 > file_size:
                        logger.warning(
                            f"Corrupt chunk sector pointer in {self.filename} for chunk ({chunk_x}, {chunk_z})"
                        )
                        continue

                    f.seek(byte_offset)
                    length_bytes = f.read(4)
                    if len(length_bytes) < 4:
                        continue
                    length = int.from_bytes(length_bytes, "big")
                    if length <= 1 or byte_offset + 4 + length > file_size:
                        logger.warning(
                            f"Invalid chunk length {length} in {self.filename} for chunk ({chunk_x}, {chunk_z})"
                        )
                        continue

                    compression_type = f.read(1)[0]
                    compressed_payload = f.read(length - 1)

                    try:
                        if compression_type == 2:
                            decompressed = zlib.decompress(compressed_payload)
                        elif compression_type == 1:
                            decompressed = gzip.decompress(compressed_payload)
                        elif compression_type == 3:
                            decompressed = compressed_payload
                        else:
                            logger.warning(
                                f"Unknown compression type {compression_type} in {self.filename} for chunk ({chunk_x}, {chunk_z})"
                            )
                            continue

                        _, root = parse_nbt(decompressed)
                        if root:
                            yield chunk_x, chunk_z, root
                    except Exception as e:
                        logger.warning(
                            f"Failed to parse NBT for chunk ({chunk_x}, {chunk_z}) in {self.filename}: {e}"
                        )
                        continue
        except Exception as e:
            logger.error(f"Error reading MCA file {self.filepath}: {e}")
