import struct
import pytest
import os
import tempfile
from app.scanner.nbt_reader import parse_nbt, NBTReader
from app.scanner.mca_reader import MCAReader

def test_nbt_basic_types():
    # Construct binary NBT: Compound with Byte(1), Short(2), Int(3), String("test")
    # Tag byte: 10 (Compound), name length 4, "root"
    # payload:
    # Tag 1 (Byte), name "b", value 42
    # Tag 3 (Int), name "num", value 1337
    # Tag 8 (String), name "s", length 5, "hello"
    # Tag 0 (End)
    data = bytearray()
    data.extend([10, 0, 4, ord('r'), ord('o'), ord('o'), ord('t')])
    # Byte tag
    data.extend([1, 0, 1, ord('b'), 42])
    # Int tag
    data.extend([3, 0, 3, ord('n'), ord('u'), ord('m')])
    data.extend(struct.pack('>i', 1337))
    # String tag
    data.extend([8, 0, 1, ord('s'), 0, 5])
    data.extend(b'hello')
    # End tag
    data.append(0)

    name, root = parse_nbt(bytes(data))
    assert name == "root"
    assert root["b"] == 42
    assert root["num"] == 1337
    assert root["s"] == "hello"

def test_nbt_list_and_arrays():
    data = bytearray()
    data.extend([10, 0, 4, ord('t'), ord('e'), ord('s'), ord('t')])
    # IntArray tag (type 11), name "ia", length 3
    data.extend([11, 0, 2, ord('i'), ord('a')])
    data.extend(struct.pack('>i', 3))
    data.extend(struct.pack('>3i', 10, 20, 30))
    # End tag
    data.append(0)

    name, root = parse_nbt(bytes(data))
    assert root["ia"] == [10, 20, 30]

def test_mca_reader_invalid_file():
    with tempfile.NamedTemporaryFile(suffix=".mca", delete=False) as f:
        f.write(b"corrupt header data")
        temp_path = f.name

    try:
        # Invalid filename pattern
        with pytest.raises(ValueError):
            MCAReader(temp_path)
    finally:
        os.remove(temp_path)

def test_mca_reader_empty_sectors():
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = os.path.join(tmpdir, "r.0.0.mca")
        with open(temp_path, "wb") as f:
            # 8KB of zeros (no generated chunks)
            f.write(b"\x00" * 8192)

        reader = MCAReader(temp_path)
        chunks = list(reader.read_chunks())
        assert len(chunks) == 0
