"""Physics engine for the loop-the-loop dynamics model."""
from .constants import BALLS, G, RAIL_RADIUS, RAIL_SPACING, BallProperties, INCHES_TO_METERS, METERS_TO_INCHES
from .geometry import compute_contact_geometry, compute_effective_loop_radius
from .energy import (frictionless_block_height, flat_rolling_height,
                     two_rail_height, compute_all_predictions, compute_waterfall)
from .ode_model import simulate
