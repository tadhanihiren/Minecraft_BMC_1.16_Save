# Underground Storage Room (9x9, Height 6) matching Pagoda style
# Centered at X=-968, Z=-296
# Width/Length: 9x9 -> X: [-972, -964], Z: [-300, -292]
# Interior Height: 6 blocks -> Y: [56, 61]
# Ceiling: Y = 62 (calcite / polished deepslate)
# Floor: Y = 55 (polished deepslate & crimson planks)
# Outer walls: X=-972, X=-964, Z=-300, Z=-292

# 1. Hollow out the interior space to air (Y 56 to 61)
fill -971 56 -299 -965 61 -293 air replace

# 2. Floor (Y=55)
fill -972 55 -300 -964 55 -292 cavesandcliffs:polished_deepslate replace
# Floor carpet / inner wood accent
fill -970 55 -298 -966 55 -294 minecraft:crimson_planks replace

# 3. Ceiling (Y=62)
fill -971 62 -299 -965 62 -293 cavesandcliffs:calcite replace
# Center lantern / light fixture on ceiling
setblock -968 62 -296 cavesandcliffs:polished_deepslate
setblock -968 61 -296 minecraft:chain
setblock -968 60 -296 minecraft:lantern[hanging=true]

# 4. Outer Walls (Y 56 to 61)
# East & West walls
fill -972 56 -300 -972 61 -292 cavesandcliffs:calcite replace
fill -964 56 -300 -964 61 -292 cavesandcliffs:calcite replace
# North & South walls
fill -971 56 -300 -965 61 -300 cavesandcliffs:calcite replace
fill -971 56 -292 -965 61 -292 cavesandcliffs:calcite replace

# 5. Corner Pillars in Crimson Stem (lacquered pagoda wood)
fill -972 56 -300 -972 61 -300 minecraft:crimson_stem[axis=y] replace
fill -964 56 -300 -964 61 -300 minecraft:crimson_stem[axis=y] replace
fill -972 56 -292 -972 61 -292 minecraft:crimson_stem[axis=y] replace
fill -964 56 -292 -964 61 -292 minecraft:crimson_stem[axis=y] replace

# Wall trimming / baseboards & cornices in polished deepslate
fill -971 56 -299 -971 56 -293 cavesandcliffs:deepslate_tile_slab[type=bottom] replace
fill -965 56 -299 -965 56 -293 cavesandcliffs:deepslate_tile_slab[type=bottom] replace
fill -970 56 -299 -966 56 -299 cavesandcliffs:deepslate_tile_slab[type=bottom] replace
fill -970 56 -293 -966 56 -293 cavesandcliffs:deepslate_tile_slab[type=bottom] replace

# Upper cornices (Y=61)
fill -971 61 -299 -971 61 -293 cavesandcliffs:deepslate_tile_stairs[half=top,facing=east] replace
fill -965 61 -299 -965 61 -293 cavesandcliffs:deepslate_tile_stairs[half=top,facing=west] replace

# Corner lanterns for cozy Japanese ambient lighting
setblock -971 59 -299 minecraft:lantern[hanging=true]
setblock -965 59 -299 minecraft:lantern[hanging=true]
setblock -971 59 -293 minecraft:lantern[hanging=true]
setblock -965 59 -293 minecraft:lantern[hanging=true]
