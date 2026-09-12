import struct
from typing import Any, Dict, List, Tuple

TAG_END = 0
TAG_BYTE = 1
TAG_SHORT = 2
TAG_INT = 3
TAG_LONG = 4
TAG_FLOAT = 5
TAG_DOUBLE = 6
TAG_BYTE_ARRAY = 7
TAG_STRING = 8
TAG_LIST = 9
TAG_COMPOUND = 10
TAG_INT_ARRAY = 11
TAG_LONG_ARRAY = 12

class NBTReader:
    """High performance binary reader for Minecraft NBT format."""
    __slots__ = ('data', 'pos', 'len')

    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0
        self.len = len(data)

    def read_byte(self) -> int:
        b = self.data[self.pos]
        self.pos += 1
        return b

    def read_sbyte(self) -> int:
        v = struct.unpack_from('>b', self.data, self.pos)[0]
        self.pos += 1
        return v

    def read_short(self) -> int:
        v = struct.unpack_from('>h', self.data, self.pos)[0]
        self.pos += 2
        return v

    def read_int(self) -> int:
        v = struct.unpack_from('>i', self.data, self.pos)[0]
        self.pos += 4
        return v

    def read_long(self) -> int:
        v = struct.unpack_from('>q', self.data, self.pos)[0]
        self.pos += 8
        return v

    def read_float(self) -> float:
        v = struct.unpack_from('>f', self.data, self.pos)[0]
        self.pos += 4
        return v

    def read_double(self) -> float:
        v = struct.unpack_from('>d', self.data, self.pos)[0]
        self.pos += 8
        return v

    def read_string(self) -> str:
        length = struct.unpack_from('>H', self.data, self.pos)[0]
        self.pos += 2
        s = self.data[self.pos:self.pos + length].decode('utf-8', errors='replace')
        self.pos += length
        return s

    def read_byte_array(self) -> bytes:
        length = self.read_int()
        data = self.data[self.pos:self.pos + length]
        self.pos += length
        return data

    def read_int_array(self) -> List[int]:
        length = self.read_int()
        if length <= 0:
            return []
        res = struct.unpack_from(f'>{length}i', self.data, self.pos)
        self.pos += length * 4
        return list(res)

    def read_long_array(self) -> List[int]:
        length = self.read_int()
        if length <= 0:
            return []
        res = struct.unpack_from(f'>{length}q', self.data, self.pos)
        self.pos += length * 8
        return list(res)

    def read_payload(self, tag_type: int) -> Any:
        if tag_type == TAG_BYTE:
            return self.read_sbyte()
        elif tag_type == TAG_SHORT:
            return self.read_short()
        elif tag_type == TAG_INT:
            return self.read_int()
        elif tag_type == TAG_LONG:
            return self.read_long()
        elif tag_type == TAG_FLOAT:
            return self.read_float()
        elif tag_type == TAG_DOUBLE:
            return self.read_double()
        elif tag_type == TAG_BYTE_ARRAY:
            return self.read_byte_array()
        elif tag_type == TAG_STRING:
            return self.read_string()
        elif tag_type == TAG_LIST:
            elem_type = self.read_byte()
            length = self.read_int()
            if length <= 0:
                return []
            # Read elements
            return [self.read_payload(elem_type) for _ in range(length)]
        elif tag_type == TAG_COMPOUND:
            comp: Dict[str, Any] = {}
            while self.pos < self.len:
                tt = self.read_byte()
                if tt == TAG_END:
                    break
                name = self.read_string()
                comp[name] = self.read_payload(tt)
            return comp
        elif tag_type == TAG_INT_ARRAY:
            return self.read_int_array()
        elif tag_type == TAG_LONG_ARRAY:
            return self.read_long_array()
        else:
            raise ValueError(f"Unknown NBT tag type {tag_type} at position {self.pos}")

    def read_root(self) -> Tuple[str, Dict[str, Any]]:
        if self.pos >= self.len:
            return "", {}
        tag_type = self.read_byte()
        if tag_type == TAG_END:
            return "", {}
        name = self.read_string()
        payload = self.read_payload(tag_type)
        return name, payload

def parse_nbt(data: bytes) -> Tuple[str, Dict[str, Any]]:
    """Parse raw decompressed NBT bytes into (root_name, dictionary)."""
    reader = NBTReader(data)
    return reader.read_root()
