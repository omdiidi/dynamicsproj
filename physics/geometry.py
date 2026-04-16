"""
Two-rail contact geometry for a sphere rolling on parallel cylindrical rails.

References:
  - Bachman (1985), "Sphere rolling down a grooved track," Am. J. Phys. 53(8), 765
  - West, Barrett & Vender (2024), "Deep in Galileo's Groove," The Physics Teacher 62(2), 104

Key insight: the effective rolling radius r_eff < R_ball because the contact
points are elevated above the lowest point of the sphere. The ball spins faster
for a given translational speed, storing more energy in rotation.

The instantaneous axis of rotation passes through the two contact points,
not through the bottom of the sphere. The lever arm for converting angular
velocity to linear velocity is r_eff, not R.
"""
import numpy as np
from .constants import RAIL_RADIUS, RAIL_SPACING


def compute_contact_geometry(R_ball: float, r_rail: float = RAIL_RADIUS,
                              s: float = RAIL_SPACING) -> dict:
    """
    Compute all derived geometric quantities for a sphere on two cylindrical rails.

    Parameters:
        R_ball: ball radius (m)
        r_rail: rail radius (m), default from constants
        s: rail center-to-center spacing (m), default from constants

    Returns dict with:
        alpha: contact half-angle (rad)
        h_offset: height of ball center above rail center plane (m)
        r_eff: effective rolling radius (m)
        beta: rotational KE multiplier = (2/5)*(R/r_eff)^2
        KE_factor: total KE factor = 1 + beta
    """
    half_s = s / 2
    R_plus_r = R_ball + r_rail

    # Verify the ball is large enough to sit on the rails
    if R_plus_r <= half_s:
        raise ValueError(
            f"Ball radius {R_ball*1000:.1f}mm + rail radius {r_rail*1000:.1f}mm "
            f"= {R_plus_r*1000:.1f}mm must exceed half-spacing {half_s*1000:.1f}mm"
        )

    # Contact half-angle: angle from vertical to line from ball center to rail center
    alpha = np.arcsin(half_s / R_plus_r)

    # Height of ball center above the plane containing rail centers
    h_offset = np.sqrt(R_plus_r**2 - half_s**2)

    # Effective rolling radius: perpendicular distance from rotation axis to CM velocity
    # r_eff = R * cos(alpha) = R * h_offset / (R + r_rail)
    r_eff = R_ball * h_offset / R_plus_r

    # Rotational KE multiplier: (2/5)*(R/r_eff)^2
    # For a solid sphere I = 2/5 mR^2, and omega = v/r_eff, so
    # KE_rot = (1/2)(2/5)mR^2 * (v/r_eff)^2 = (1/5)m(R/r_eff)^2 * v^2
    beta = (2.0 / 5.0) * (R_ball / r_eff) ** 2

    # Total KE = (1/2)mv^2 * KE_factor where KE_factor = 1 + beta
    KE_factor = 1.0 + beta

    return {
        "alpha": alpha,
        "h_offset": h_offset,
        "r_eff": r_eff,
        "beta": beta,
        "KE_factor": KE_factor,
    }


def compute_effective_loop_radius(R_loop: float, h_offset: float) -> float:
    """
    CM path radius inside the loop.

    The ball center is offset inward from the rail surface by h_offset,
    so the CM traces a circle of radius R_loop - h_offset.
    """
    return R_loop - h_offset
