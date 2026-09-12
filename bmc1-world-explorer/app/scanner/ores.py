from dataclasses import dataclass
from typing import List, Tuple, Dict
from collections import deque

@dataclass
class OreVein:
    ore_id: str
    center_x: int
    center_y: int
    center_z: int
    block_count: int
    min_x: int
    max_x: int
    min_y: int
    max_y: int
    min_z: int
    max_z: int
    blocks: List[Tuple[int, int, int]]

def cluster_ore_veins(ore_blocks: List[Tuple[str, int, int, int]]) -> List[OreVein]:
    """
    Cluster adjacent ore blocks of the same type into coherent ore veins.
    Two blocks belong to the same vein if Chebyshev/Manhattan distance <= 2.
    """
    if not ore_blocks:
        return []

    # Group blocks by ore_id
    by_ore: Dict[str, List[Tuple[int, int, int]]] = {}
    for ore_id, x, y, z in ore_blocks:
        by_ore.setdefault(ore_id, []).append((x, y, z))

    veins: List[OreVein] = []

    for ore_id, coords in by_ore.items():
        coords_set = set(coords)
        visited = set()

        for start_pos in coords:
            if start_pos in visited:
                continue

            # BFS to find connected vein component
            queue = deque([start_pos])
            visited.add(start_pos)
            cluster: List[Tuple[int, int, int]] = []

            while queue:
                current = queue.popleft()
                cluster.append(current)
                cx, cy, cz = current

                # Check 26-neighborhood with distance <= 2
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        for dz in (-1, 0, 1):
                            if dx == 0 and dy == 0 and dz == 0:
                                continue
                            neighbor = (cx + dx, cy + dy, cz + dz)
                            if neighbor in coords_set and neighbor not in visited:
                                visited.add(neighbor)
                                queue.append(neighbor)

            xs = [p[0] for p in cluster]
            ys = [p[1] for p in cluster]
            zs = [p[2] for p in cluster]

            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            min_z, max_z = min(zs), max(zs)

            center_x = round(sum(xs) / len(xs))
            center_y = round(sum(ys) / len(ys))
            center_z = round(sum(zs) / len(zs))

            veins.append(
                OreVein(
                    ore_id=ore_id,
                    center_x=center_x,
                    center_y=center_y,
                    center_z=center_z,
                    block_count=len(cluster),
                    min_x=min_x,
                    max_x=max_x,
                    min_y=min_y,
                    max_y=max_y,
                    min_z=min_z,
                    max_z=max_z,
                    blocks=cluster
                )
            )

    return veins
