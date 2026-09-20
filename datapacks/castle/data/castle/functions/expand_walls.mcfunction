# --- CLONE TOWERS ---
clone -936 65 -336 -928 84 -326 -920 65 -336 replace
clone -1008 65 -265 -999 84 -256 -1008 65 -233 replace
clone -936 65 -265 -922 84 -256 -920 65 -233 replace
# --- CLEAR OLD WALLS & TOWERS ---
fill -936 69 -336 -928 84 -326 air replace
fill -936 69 -265 -922 84 -256 air replace
fill -1008 69 -265 -999 84 -256 air replace
fill -930 69 -325 -928 75 -266 air replace
fill -998 69 -258 -937 75 -256 air replace
# --- EXTEND NORTH WALL ---
fill -928 67 -336 -921 68 -336 stone_bricks replace
fill -928 69 -336 -921 69 -336 stone_brick_wall replace
# --- EXTEND WEST WALL ---
fill -1008 67 -255 -1008 68 -234 stone_bricks replace
fill -1008 69 -255 -1008 69 -234 stone_brick_wall replace
# --- BUILD NEW EAST WALL ---
fill -912 67 -325 -912 68 -234 stone_bricks replace
fill -912 69 -325 -912 69 -234 stone_brick_wall replace
# --- BUILD NEW SOUTH WALL ---
fill -998 67 -224 -921 68 -224 stone_bricks replace
fill -998 69 -224 -921 69 -224 stone_brick_wall replace
# --- LEVEL EXPANSION COURTYARD ---
fill -1007 70 -255 -913 90 -225 air replace
fill -1007 68 -255 -913 68 -225 grass_block replace
fill -1007 60 -255 -913 67 -225 dirt replace
