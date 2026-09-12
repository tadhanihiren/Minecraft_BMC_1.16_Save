import pytest
from app.scanner.mca_reader import (
    parse_region_coords,
    chunk_coords_to_block_coords,
    block_coords_to_chunk_coords,
    chunk_coords_to_region_coords
)

def test_parse_region_coords():
    assert parse_region_coords("r.0.0.mca") == (0, 0)
    assert parse_region_coords("r.-1.-1.mca") == (-1, -1)
    assert parse_region_coords("r.-2.3.mca") == (-2, 3)
    assert parse_region_coords("r.10.-5.mca") == (10, -5)
    assert parse_region_coords("invalid.mca") is None
    assert parse_region_coords("r.0.mca") is None

def test_chunk_to_block_coords():
    # Chunk (0, 0)
    assert chunk_coords_to_block_coords(0, 0) == (0, 0)
    assert chunk_coords_to_block_coords(0, 0, 15, 15) == (15, 15)

    # Negative chunk (-1, -1)
    assert chunk_coords_to_block_coords(-1, -1) == (-16, -16)
    assert chunk_coords_to_block_coords(-1, -1, 15, 15) == (-1, -1)

    # Region boundary chunk (31, 31)
    assert chunk_coords_to_block_coords(31, 31) == (496, 496)

def test_block_to_chunk_coords():
    assert block_coords_to_chunk_coords(0, 0) == (0, 0)
    assert block_coords_to_chunk_coords(15, 15) == (0, 0)
    assert block_coords_to_chunk_coords(16, 16) == (1, 1)

    # Negative coordinates
    assert block_coords_to_chunk_coords(-1, -1) == (-1, -1)
    assert block_coords_to_chunk_coords(-16, -16) == (-1, -1)
    assert block_coords_to_chunk_coords(-17, -17) == (-2, -2)

def test_chunk_to_region_coords():
    assert chunk_coords_to_region_coords(0, 0) == (0, 0)
    assert chunk_coords_to_region_coords(31, 31) == (0, 0)
    assert chunk_coords_to_region_coords(32, 32) == (1, 1)
    assert chunk_coords_to_region_coords(-1, -1) == (-1, -1)
    assert chunk_coords_to_region_coords(-32, -32) == (-1, -1)
    assert chunk_coords_to_region_coords(-33, -33) == (-2, -2)

def test_minecraft_block_flooring():
    import math
    # In Minecraft, world coordinates inside block X=-85 (spanning [-85.0, -84.0))
    # must floor to -85, NOT round to -84
    assert math.floor(-84.3) == -85
    assert math.floor(-84.9) == -85
    assert math.floor(-85.0) == -85
    assert math.floor(-8.2) == -9

