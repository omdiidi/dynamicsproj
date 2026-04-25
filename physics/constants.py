"""
Known constants and ball/track data for the loop-the-loop project.
All values from the ME 2030 project description unless noted otherwise.

Dynamics principles: This file contains the given physical parameters
for the three test spheres and the track geometry. Heights are measured
relative to the bottom of the loop (the competition datum).
"""
import numpy as np
from dataclasses import dataclass

G = 9.81  # m/s^2, gravitational acceleration

# Track geometry (given in project description)
# DATUM: All heights measured from the track surface at the bottom of the loop.
# The project says "drop heights should be given relative to the bottom of the loop."
RAIL_DIAMETER_MM = 3.0
RAIL_RADIUS_MM = RAIL_DIAMETER_MM / 2          # 1.5 mm
RAIL_OUTSIDE_SPACING_MM = 17.0
# Center-to-center = outside-to-outside minus one diameter:
# 17mm outside-to-outside - 3mm rail diameter = 14mm center-to-center
RAIL_CENTER_SPACING_MM = RAIL_OUTSIDE_SPACING_MM - RAIL_DIAMETER_MM  # 14.0 mm

# Convert to meters for calculations
RAIL_RADIUS = RAIL_RADIUS_MM / 1000
RAIL_SPACING = RAIL_CENTER_SPACING_MM / 1000    # 0.014 m center-to-center

# Unit conversions
INCHES_TO_METERS = 0.0254
METERS_TO_INCHES = 1 / INCHES_TO_METERS

@dataclass
class BallProperties:
    """Physical and modeling properties for one of the three test spheres."""
    name: str
    mass_kg: float
    radius_m: float
    mu_sliding: float          # sliding friction coefficient
    C_rr: float                # rolling resistance coefficient (tunable default)
    color: str                 # for plotting

BALLS = {
    "Steel": BallProperties(
        name="Stainless Steel",
        mass_kg=0.011,
        radius_m=0.007,
        mu_sliding=0.213,       # tan(12 deg), from friction test
        C_rr=0.002,             # default, tunable
        color="#4A90D9",
    ),
    "Plastic": BallProperties(
        name="Plastic",
        mass_kg=0.003,
        radius_m=0.0075,
        mu_sliding=0.213,       # tan(12 deg), from friction test
        C_rr=0.015,             # default, tunable
        color="#E8A838",
    ),
    "Rubber": BallProperties(
        name="Nitrile Rubber",
        mass_kg=0.0028,
        radius_m=0.00795,
        mu_sliding=0.35,        # estimated (tipped before slipping, so > 0.213)
        C_rr=0.08,              # default, tunable (significant due to hysteresis)
        color="#D94A4A",
    ),
}
