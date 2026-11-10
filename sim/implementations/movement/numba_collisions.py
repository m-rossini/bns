"""Numba-accelerated collision detection for bean movement.

This module provides fast collision detection using numba JIT compilation.
The functions operate on raw numpy arrays for maximum performance.
"""

from __future__ import annotations

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:  # pragma: no cover
    NUMPY_AVAILABLE = False
    np = None  # type: ignore

try:
    from numba import njit
    NUMBA_AVAILABLE = True
except ImportError:  # pragma: no cover
    NUMBA_AVAILABLE = False

    def njit(*args, **kwargs):  # type: ignore
        def decorator(func):
            return func
        return decorator

# The numba kernels operate on numpy arrays, so a missing numpy disables the
# fast path even when numba itself is installed. Callers fall back to the pure
# Python collision loops in ``straight_line``.
if not NUMPY_AVAILABLE:  # pragma: no cover
    NUMBA_AVAILABLE = False


@njit(cache=True, fastmath=True)
def _overlaps_barrier_rect(bean_x: float, bean_y: float, radius: float,
                           bx: float, by: float, bw: float, bh: float) -> bool:
    """Check bean-barrier overlap for rectangular barriers."""
    left, bottom = bx, by
    right, top = bx + bw, by + bh
    cx = min(max(bean_x, left), right)
    cy = min(max(bean_y, bottom), top)
    dx, dy = bean_x - cx, bean_y - cy
    return dx * dx + dy * dy <= radius * radius


@njit(cache=True, fastmath=True)
def _overlaps_barrier_circle(bean_x: float, bean_y: float, radius: float,
                             cx: float, cy: float, barrier_radius: float) -> bool:
    """Check bean-barrier overlap for circular barriers."""
    dx, dy = bean_x - cx, bean_y - cy
    reach = radius + barrier_radius
    return dx * dx + dy * dy <= reach * reach


@njit(cache=True, fastmath=True)
def _check_barrier_collisions(
    bean_x: np.ndarray,
    bean_y: np.ndarray,
    bean_ids: np.ndarray,
    radius: float,
    barrier_kinds: np.ndarray,  # 0=rect, 1=circle
    barrier_x: np.ndarray,
    barrier_y: np.ndarray,
    barrier_w: np.ndarray,
    barrier_h: np.ndarray,
    barrier_radius: np.ndarray,
    barrier_ids: np.ndarray,
    collisions_out: np.ndarray,  # pre-allocated (n_beans * n_barriers, 2)
) -> int:
    """
    Check all bean-barrier collisions using numba.

    Returns the number of collisions found. Collisions are written to
    `collisions_out` as (bean_idx, barrier_idx) pairs.
    """
    n_beans = bean_x.shape[0]
    n_barriers = barrier_x.shape[0]
    count = 0

    for i in range(n_beans):
        bx = bean_x[i]
        by = bean_y[i]
        for j in range(n_barriers):
            kind = barrier_kinds[j]
            hit = False
            if kind == 0:  # rect
                hit = _overlaps_barrier_rect(
                    bx, by, radius,
                    barrier_x[j], barrier_y[j],
                    barrier_w[j], barrier_h[j]
                )
            elif kind == 1:  # circle
                hit = _overlaps_barrier_circle(
                    bx, by, radius,
                    barrier_x[j], barrier_y[j],
                    barrier_radius[j]
                )
            if hit:
                if count < collisions_out.shape[0]:
                    collisions_out[count, 0] = i
                    collisions_out[count, 1] = j
                    count += 1
    return count


@njit(cache=True, fastmath=True)
def _check_bean_collisions(
    bean_x: np.ndarray,
    bean_y: np.ndarray,
    bean_ids: np.ndarray,
    radius: float,
    cell_size: float,
    world_width: float,
    world_height: float,
    collisions_out: np.ndarray,  # pre-allocated (max_pairs, 2)
) -> int:
    """
    Check bean-bean collisions using spatial hashing (numba version).

    Uses a fixed grid with cell_size = 2 * radius. Returns collision pairs
    as indices into the bean arrays.
    """
    n_beans = bean_x.shape[0]
    if n_beans < 2:
        return 0

    # Spatial hash: map cell -> list of bean indices
    # We use a flat array for cells: cell_x * n_cells_y + cell_y
    n_cells_x = max(1, int(world_width / cell_size) + 1)
    n_cells_y = max(1, int(world_height / cell_size) + 1)
    n_cells = n_cells_x * n_cells_y

    # Count beans per cell
    cell_counts = np.zeros(n_cells, dtype=np.int32)
    bean_cells = np.zeros(n_beans, dtype=np.int32)

    for i in range(n_beans):
        cx = int(bean_x[i] // cell_size)
        cy = int(bean_y[i] // cell_size)
        if cx < 0: cx = 0
        if cx >= n_cells_x: cx = n_cells_x - 1
        if cy < 0: cy = 0
        if cy >= n_cells_y: cy = n_cells_y - 1
        cell_idx = cx * n_cells_y + cy
        bean_cells[i] = cell_idx
        cell_counts[cell_idx] += 1

    # Build cell -> bean indices mapping (using a flat array with offsets)
    cell_offsets = np.zeros(n_cells + 1, dtype=np.int32)
    for i in range(n_cells):
        cell_offsets[i + 1] = cell_offsets[i] + cell_counts[i]

    total_in_cells = cell_offsets[-1]
    cell_beans = np.zeros(total_in_cells, dtype=np.int32)
    cell_pos = cell_offsets.copy()

    for i in range(n_beans):
        cell_idx = bean_cells[i]
        pos = cell_pos[cell_idx]
        cell_beans[pos] = i
        cell_pos[cell_idx] = pos + 1

    # Check collisions within and between adjacent cells
    reach_sq = (2.0 * radius) ** 2
    count = 0
    max_pairs = collisions_out.shape[0]

    for cx in range(n_cells_x):
        for cy in range(n_cells_y):
            cell_idx = cx * n_cells_y + cy
            start = cell_offsets[cell_idx]
            end = cell_offsets[cell_idx + 1]
            if start >= end:
                continue

            # Check against this cell and 8 neighbors
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    ncx = cx + dx
                    ncy = cy + dy
                    if ncx < 0 or ncx >= n_cells_x or ncy < 0 or ncy >= n_cells_y:
                        continue
                    n_idx = ncx * n_cells_y + ncy
                    n_start = cell_offsets[n_idx]
                    n_end = cell_offsets[n_idx + 1]
                    if n_start >= n_end:
                        continue

                    # Check all pairs
                    for ii in range(start, end):
                        a = cell_beans[ii]
                        for jj in range(n_start, n_end):
                            b = cell_beans[jj]
                            if a >= b:  # avoid duplicate and self
                                continue
                            ddx = bean_x[a] - bean_x[b]
                            ddy = bean_y[a] - bean_y[b]
                            if ddx * ddx + ddy * ddy < reach_sq:
                                if count < max_pairs:
                                    collisions_out[count, 0] = a
                                    collisions_out[count, 1] = b
                                    count += 1
    return count


def check_barrier_collisions_numba(
    beans, barriers, radius: float
) -> list[tuple[int, int]]:
    """
    Check bean-barrier collisions using numba.

    Returns list of (bean_idx, barrier_idx) tuples for collisions.
    """
    if not NUMBA_AVAILABLE or not beans or not barriers:
        return []

    n_beans = len(beans)
    n_barriers = len(barriers)

    # Extract bean data
    bean_x = np.array([b.x for b in beans], dtype=np.float64)
    bean_y = np.array([b.y for b in beans], dtype=np.float64)
    bean_ids = np.array([b.id for b in beans], dtype=np.int64)

    # Extract barrier data
    barrier_kinds = np.zeros(n_barriers, dtype=np.int8)  # 0=rect, 1=circle
    barrier_x = np.zeros(n_barriers, dtype=np.float64)
    barrier_y = np.zeros(n_barriers, dtype=np.float64)
    barrier_w = np.zeros(n_barriers, dtype=np.float64)
    barrier_h = np.zeros(n_barriers, dtype=np.float64)
    barrier_radius = np.zeros(n_barriers, dtype=np.float64)
    barrier_ids = np.array([b.id for b in barriers], dtype=np.int64)

    for j, bar in enumerate(barriers):
        if bar.kind == "rect":
            barrier_kinds[j] = 0
            barrier_x[j] = bar.x
            barrier_y[j] = bar.y
            barrier_w[j] = bar.width
            barrier_h[j] = bar.height
        elif bar.kind == "circle":
            barrier_kinds[j] = 1
            barrier_x[j] = bar.x
            barrier_y[j] = bar.y
            barrier_radius[j] = bar.radius

    # Pre-allocate output (max possible collisions = n_beans * n_barriers)
    max_collisions = n_beans * n_barriers
    collisions_out = np.zeros((max_collisions, 2), dtype=np.int32)

    count = _check_barrier_collisions(
        bean_x, bean_y, bean_ids, radius,
        barrier_kinds, barrier_x, barrier_y, barrier_w, barrier_h, barrier_radius,
        barrier_ids, collisions_out
    )

    return [(int(collisions_out[i, 0]), int(collisions_out[i, 1])) for i in range(count)]


def check_bean_collisions_numba(
    beans, radius: float, world_width: float, world_height: float
) -> list[tuple[int, int]]:
    """
    Check bean-bean collisions using numba spatial hash.

    Returns list of (bean_idx_a, bean_idx_b) tuples for collisions.
    """
    if not NUMBA_AVAILABLE or len(beans) < 2:
        return []

    n_beans = len(beans)
    bean_x = np.array([b.x for b in beans], dtype=np.float64)
    bean_y = np.array([b.y for b in beans], dtype=np.float64)
    bean_ids = np.array([b.id for b in beans], dtype=np.int64)

    cell_size = max(1.0, 2.0 * radius)

    # Estimate max pairs: each bean can collide with ~8 neighbors in dense packing
    max_pairs = n_beans * 16
    collisions_out = np.zeros((max_pairs, 2), dtype=np.int32)

    count = _check_bean_collisions(
        bean_x, bean_y, bean_ids, radius,
        cell_size, world_width, world_height, collisions_out
    )

    return [(int(collisions_out[i, 0]), int(collisions_out[i, 1])) for i in range(count)]