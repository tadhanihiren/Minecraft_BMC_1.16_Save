# Expanded Underground Storage Room (18x18, Height 6) matching Pagoda style
# Centered at X=-968, Z=-296
# 18 blocks wide: X from -977 to -960
# 18 blocks long: Z from -305 to -288
# Interior Height: 6 blocks -> Y: 56 to 61
# Ceiling: Y = 62 (calcite / polished deepslate)
# Floor: Y = 55 (polished deepslate & crimson planks)

# 1. Hollow out the interior space to air (Y 56 to 61)
fill -976 56 -304 -961 61 -289 air replace

# 2. Floor (Y=55)
fill -977 55 -305 -960 55 -288 cavesandcliffs:polished_deepslate replace
# Large crimson wood floor inlay
fill -975 55 -303 -962 55 -290 minecraft:crimson_planks replace
# Inner polished deepslate decorative center cross / grid
fill -969 55 -303 -968 55 -290 cavesandcliffs:polished_deepslate replace
fill -975 55 -297 -962 55 -296 cavesandcliffs:polished_deepslate replace

# 3. Ceiling (Y=62)
fill -976 62 -304 -961 62 -289 cavesandcliffs:calcite replace
# Ceiling deepslate beams matching the 18x18 structure
fill -969 62 -304 -968 62 -289 cavesandcliffs:polished_deepslate replace
fill -976 62 -297 -961 62 -296 cavesandcliffs:polished_deepslate replace

# 4. Outer Walls (Y 56 to 61)
# East & West walls
fill -977 56 -305 -977 61 -288 cavesandcliffs:calcite replace
fill -960 56 -305 -960 61 -288 cavesandcliffs:calcite replace
# North & South walls
fill -976 56 -305 -961 61 -305 cavesandcliffs:calcite replace
fill -976 56 -288 -961 61 -288 cavesandcliffs:calcite replace

# 5. Crimson Wood Pillars (Corners & Wall dividing posts)
# Corner Pillars
fill -977 56 -305 -977 61 -305 minecraft:crimson_stem[axis=y] replace
fill -960 56 -305 -960 61 -305 minecraft:crimson_stem[axis=y] replace
fill -977 56 -288 -977 61 -288 minecraft:crimson_stem[axis=y] replace
fill -960 56 -288 -960 61 -288 minecraft:crimson_stem[axis=y] replace

# Wall support pillars (spaced every 6 blocks)
fill -977 56 -297 -977 61 -296 minecraft:crimson_stem[axis=y] replace
fill -960 56 -297 -960 61 -296 minecraft:crimson_stem[axis=y] replace
fill -969 56 -305 -968 61 -305 minecraft:crimson_stem[axis=y] replace
fill -969 56 -288 -968 61 -288 minecraft:crimson_stem[axis=y] replace

# 6. Baseboard trimmings (Y=56)
fill -976 56 -304 -976 56 -289 cavesandcliffs:deepslate_tile_slab[type=bottom] replace
fill -961 56 -304 -961 56 -289 cavesandcliffs:deepslate_tile_slab[type=bottom] replace
fill -975 56 -304 -962 56 -304 cavesandcliffs:deepslate_tile_slab[type=bottom] replace
fill -975 56 -289 -962 56 -289 cavesandcliffs:deepslate_tile_slab[type=bottom] replace

# 7. Upper crown cornices (Y=61)
fill -976 61 -304 -976 61 -289 cavesandcliffs:deepslate_tile_stairs[half=top,facing=east] replace
fill -961 61 -304 -961 61 -289 cavesandcliffs:deepslate_tile_stairs[half=top,facing=west] replace

# 8. Symmetrical Hanging Lanterns
setblock -969 61 -297 minecraft:chain
setblock -969 60 -297 minecraft:lantern[hanging=true]
setblock -968 61 -297 minecraft:chain
setblock -968 60 -297 minecraft:lantern[hanging=true]
setblock -969 61 -296 minecraft:chain
setblock -969 60 -296 minecraft:lantern[hanging=true]
setblock -968 61 -296 minecraft:chain
setblock -968 60 -296 minecraft:lantern[hanging=true]

# Corner lanterns
setblock -975 60 -303 minecraft:lantern[hanging=true]
setblock -962 60 -303 minecraft:lantern[hanging=true]
setblock -975 60 -290 minecraft:lantern[hanging=true]
setblock -962 60 -290 minecraft:lantern[hanging=true]
