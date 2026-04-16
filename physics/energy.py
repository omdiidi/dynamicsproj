"""
Analytical energy-balance solver for minimum release height.

Three models:
  1. Frictionless sliding block (reference case)
  2. Rolling sphere on flat surface (reference case)
  3. Rolling sphere on two rails with losses (prediction model)

Plus a waterfall breakdown function that shows how each physics correction
incrementally builds the prediction — directly generates content for the
memo appendix (30/100 points for equation development).

Dynamics principles:
  - Work-energy theorem (energy conservation from release to loop top)
  - Rotational dynamics (rolling without slipping, I = 2/5 mR^2)
  - Two-rail contact geometry (Bachman 1985)
  - Newton's 2nd law radial (centripetal condition at loop top)
"""
import numpy as np
from .constants import G, METERS_TO_INCHES, INCHES_TO_METERS, BallProperties
from .geometry import compute_contact_geometry, compute_effective_loop_radius


def frictionless_block_height(R_loop: float) -> float:
    """
    Reference case 1: frictionless sliding block.

    Energy conservation: mgh = mg(2R) + (1/2)mv^2
    Critical condition at top: v^2 = gR (from N=0 in centripetal eq)
    Result: h_min = (5/2) * R_loop
    """
    return 2.5 * R_loop


def flat_rolling_height(R_loop: float) -> float:
    """
    Reference case 2: sphere rolling without slipping on flat surface.

    Energy conservation with rotation: mgh = mg(2R) + (7/10)mv^2
    where (7/10) comes from KE_trans + KE_rot = (1/2)mv^2 + (1/5)mv^2
    Critical condition at top: v^2 = gR
    Result: h_min = (27/10) * R_loop = 2.7 * R_loop
    """
    return 2.7 * R_loop


def two_rail_height(ball: BallProperties, R_loop: float, theta_deg: float,
                    C_rr: float = None, f_transition: float = 0.0,
                    safety_margin: float = 0.0) -> dict:
    """
    Prediction model: minimum release height for a sphere rolling on two rails
    to complete a vertical circular loop.

    Parameters:
        ball: BallProperties dataclass
        R_loop: loop radius in meters (rail centerline)
        theta_deg: ramp angle in degrees from horizontal
        C_rr: rolling resistance coefficient (overrides ball default if given)
        f_transition: fraction of KE lost at ramp-to-loop transition (0 to 1)
        safety_margin: additional height in meters added to prediction

    Returns dict with h_min_m, h_min_in, h_predicted_in, and energy breakdown.
    """
    if C_rr is None:
        C_rr = ball.C_rr

    theta = np.radians(theta_deg)
    geom = compute_contact_geometry(ball.radius_m)
    h_off = geom["h_offset"]
    r_eff = geom["r_eff"]
    KE_factor = geom["KE_factor"]
    R_c = compute_effective_loop_radius(R_loop, h_off)

    if R_c <= 0:
        raise ValueError(
            f"Effective loop radius R_c = {R_c*1000:.1f}mm is non-positive. "
            f"Loop radius {R_loop*1000:.1f}mm is too small for ball offset {h_off*1000:.1f}mm."
        )

    # Critical speed squared at loop top (Newton's 2nd law, radial, N=0)
    v_top_sq = G * R_c

    # KE at loop top = (1/2) * m * v_top^2 * KE_factor
    KE_top = 0.5 * ball.mass_kg * v_top_sq * KE_factor

    # Rolling resistance in the loop
    # N_avg over a full loop ~ 3*m*g for a ball barely completing
    # (centripetal term averages to 2mg, gravity component averages to mg)
    # Path length = 2*pi*R_c
    W_loop_rr = C_rr * ball.mass_kg * G * 3.0 * (2 * np.pi * R_c)

    # Full energy balance from release to loop top:
    # m*g*[h + h_off*cos(theta)] = m*g*[2R_loop - h_off] + KE_top + W_ramp + W_loop + W_transition
    #
    # W_ramp = C_rr * m*g * h / tan(theta)              [linear in h]
    # W_transition ~ f_transition * m*g * [h - h_off*(1-cos(theta))]  [linear in h]
    #
    # Collecting h terms on LHS:
    # m*g*h * [1 - C_rr/tan(theta) - f_transition] = RHS (constants)

    rhs = (ball.mass_kg * G * (2 * R_loop - h_off * (1 + np.cos(theta)))
           + KE_top + W_loop_rr
           - f_transition * ball.mass_kg * G * h_off * (1 - np.cos(theta)))

    lhs_coefficient = ball.mass_kg * G * (1 - C_rr / np.tan(theta) - f_transition)

    if lhs_coefficient <= 0:
        h_min = float('inf')
    else:
        h_min = rhs / lhs_coefficient

    h_min_in = h_min * METERS_TO_INCHES
    h_predicted_in = np.ceil((h_min_in + safety_margin * METERS_TO_INCHES) * 10) / 10

    return {
        "h_min_m": h_min,
        "h_min_in": h_min_in,
        "h_predicted_in": h_predicted_in,
        "geom": geom,
        "R_c": R_c,
        "v_top_sq": v_top_sq,
        "KE_top": KE_top,
        "W_loop_rr": W_loop_rr,
        "KE_factor": KE_factor,
    }


def compute_all_predictions(R_loop_in: float, theta_deg: float,
                             balls: dict, C_rr_overrides: dict = None,
                             f_transition: float = 0.0,
                             safety_margin_in: float = 0.0) -> dict:
    """
    Compute predictions for all balls and both reference cases.

    Parameters:
        R_loop_in: loop radius in inches
        theta_deg: ramp angle in degrees
        balls: dict of BallProperties
        C_rr_overrides: dict {ball_name: C_rr_value}
        f_transition: transition loss fraction
        safety_margin_in: safety margin in inches
    """
    R_loop = R_loop_in * INCHES_TO_METERS
    safety_m = safety_margin_in * INCHES_TO_METERS

    results = {
        "R_loop_in": R_loop_in,
        "theta_deg": theta_deg,
        "ref_block_in": frictionless_block_height(R_loop) * METERS_TO_INCHES,
        "ref_rolling_in": flat_rolling_height(R_loop) * METERS_TO_INCHES,
        "balls": {},
    }

    for name, ball in balls.items():
        C_rr = C_rr_overrides.get(name, ball.C_rr) if C_rr_overrides else ball.C_rr
        pred = two_rail_height(ball, R_loop, theta_deg, C_rr=C_rr,
                               f_transition=f_transition, safety_margin=safety_m)
        results["balls"][name] = pred

    return results


def compute_waterfall(ball: BallProperties, R_loop: float, theta_deg: float,
                      C_rr: float = None, f_transition: float = 0.0,
                      safety_margin_in: float = 0.0) -> list:
    """
    Compute the waterfall breakdown showing how each correction changes
    the predicted height. Returns a list of dicts, one per step.

    This directly generates content for the memo appendix (30/100 points
    for "clear presentation of equation development").

    Each step adds one physics correction on top of the previous result.
    """
    if C_rr is None:
        C_rr = ball.C_rr

    theta = np.radians(theta_deg)
    geom = compute_contact_geometry(ball.radius_m)
    h_off = geom["h_offset"]
    r_eff = geom["r_eff"]
    R_c = compute_effective_loop_radius(R_loop, h_off)
    KE_factor = geom["KE_factor"]
    v_top_sq = G * R_c

    steps = []

    # Step 1: Frictionless sliding block
    h1 = 2.5 * R_loop
    steps.append({
        "step": 1,
        "name": "Frictionless sliding block",
        "principle": "Energy conservation (no rotation, no friction)",
        "formula": "h = 5/2 * R_loop",
        "latex": r"T_1 + V_1 = T_2 + V_2 \quad\Rightarrow\quad \frac{1}{2}mv_{\text{top}}^2 + mg(2R) = mgh \quad\Rightarrow\quad h = \frac{5}{2}R",
        "h_m": h1,
        "h_in": h1 * METERS_TO_INCHES,
        "delta_in": 0.0,
        "source": "Fundamental - Work-Energy Theorem",
    })

    # Step 2: Add rotation (flat surface rolling)
    h2 = 2.7 * R_loop
    steps.append({
        "step": 2,
        "name": "Add rotational KE (flat surface)",
        "principle": "Rolling without slipping, I = 2/5 mR^2, KE_rot = 1/5 mv^2",
        "formula": "h = 27/10 * R_loop",
        "latex": r"T = \frac{1}{2}mv_G^2 + \frac{1}{2}I_G\omega^2, \quad I_G = \frac{2}{5}mR^2, \quad \omega = \frac{v}{R} \quad\Rightarrow\quad T = \frac{7}{10}mv^2 \quad\Rightarrow\quad h = \frac{27}{10}R",
        "h_m": h2,
        "h_in": h2 * METERS_TO_INCHES,
        "delta_in": (h2 - h1) * METERS_TO_INCHES,
        "source": "Rotational dynamics - rolling constraint v = wR",
    })

    # Step 3: Two-rail geometry correction (no losses yet)
    h3 = (2 * R_loop - h_off * (1 + np.cos(theta))) + R_c * KE_factor / 2
    steps.append({
        "step": 3,
        "name": "Two-rail geometry correction",
        "principle": (f"Effective rolling radius r_eff = {r_eff*1000:.2f} mm < R = {ball.radius_m*1000:.1f} mm. "
                      f"Ball spins faster, KE_factor = {KE_factor:.3f} (vs 1.4 on flat). "
                      f"CM path radius R_c = R_loop - h_offset = {R_c*1000:.1f} mm."),
        "formula": "r_eff = R * h_offset / (R + r_rail); KE_factor = 1 + 2/5 * (R/r_eff)^2",
        "latex": (
            r"r_{\text{eff}} = \frac{R \cdot h_{\text{offset}}}{R + r_{\text{rail}}}, \quad"
            r"\omega = \frac{v}{r_{\text{eff}}}, \quad"
            r"T = \frac{1}{2}mv^2\!\left[1 + \frac{2}{5}\!\left(\frac{R}{r_{\text{eff}}}\right)^{\!2}\right]"
        ),
        "h_m": h3,
        "h_in": h3 * METERS_TO_INCHES,
        "delta_in": (h3 - h2) * METERS_TO_INCHES,
        "source": "Bachman (1985), Am. J. Phys. 53(8), 765",
    })

    # Step 4: Add rolling resistance
    # Solve from scratch with rolling resistance (same structure as two_rail_height)
    W_loop_rr = C_rr * ball.mass_kg * G * 3.0 * (2 * np.pi * R_c)
    rhs4 = (ball.mass_kg * G * (2 * R_loop - h_off * (1 + np.cos(theta)))
            + 0.5 * ball.mass_kg * v_top_sq * KE_factor + W_loop_rr)
    lhs4 = ball.mass_kg * G * (1 - C_rr / np.tan(theta))
    h4 = rhs4 / lhs4 if lhs4 > 0 else float('inf')
    steps.append({
        "step": 4,
        "name": "Add rolling resistance",
        "principle": (f"C_rr = {C_rr:.3f}. Ramp loss = C_rr*mg*h/tan(theta). "
                      f"Loop loss = C_rr*mg*3*(2*pi*R_c) with N_avg ~ 3mg."),
        "formula": "W_rr = C_rr * N * ds (integrated over path)",
        "latex": r"U_{NC} = \int \mathbf{F} \cdot d\mathbf{r} = C_{rr} \int N\, ds, \quad W_{\text{ramp}} = \frac{C_{rr}\, mg\, h}{\tan\theta}, \quad W_{\text{loop}} = C_{rr}\cdot 3mg \cdot 2\pi R_c",
        "h_m": h4,
        "h_in": h4 * METERS_TO_INCHES,
        "delta_in": (h4 - h3) * METERS_TO_INCHES,
        "source": "Rolling resistance (engineering literature)",
    })

    # Step 5: Add transition loss
    if f_transition > 0:
        rhs5 = (ball.mass_kg * G * (2 * R_loop - h_off * (1 + np.cos(theta)))
                + 0.5 * ball.mass_kg * v_top_sq * KE_factor + W_loop_rr
                - f_transition * ball.mass_kg * G * h_off * (1 - np.cos(theta)))
        lhs5 = ball.mass_kg * G * (1 - C_rr / np.tan(theta) - f_transition)
        h5 = rhs5 / lhs5 if lhs5 > 0 else float('inf')
    else:
        h5 = h4
    steps.append({
        "step": 5,
        "name": "Add transition loss",
        "principle": (f"f_transition = {f_transition:.0%} of KE lost at ramp-to-loop junction "
                      f"due to abrupt curvature change."),
        "formula": "W_trans = f_trans * KE_entry",
        "latex": r"W_{\text{trans}} = f_{\text{trans}} \cdot T_{\text{entry}} \quad \text{(Wang et al. 2021: jerk at curvature discontinuity)}",
        "h_m": h5,
        "h_in": h5 * METERS_TO_INCHES,
        "delta_in": (h5 - h4) * METERS_TO_INCHES,
        "source": "Wang et al. (2021), Am. J. Phys. 89(6), 583",
    })

    # Step 6: Safety margin
    h6_in = np.ceil((h5 * METERS_TO_INCHES + safety_margin_in) * 10) / 10
    steps.append({
        "step": 6,
        "name": "Safety margin",
        "principle": (f"+{safety_margin_in:.1f} in margin, rounded UP to 0.1 in. "
                      f"Accounts for trial-to-trial variability (3 successive trials required)."),
        "formula": "h_final = ceil((h_min + margin) * 10) / 10",
        "latex": r"h_{\text{final}} = \left\lceil (h_{\min} + \Delta h_{\text{margin}}) \times 10 \right\rceil / 10",
        "h_m": h6_in * INCHES_TO_METERS,
        "h_in": h6_in,
        "delta_in": h6_in - h5 * METERS_TO_INCHES,
        "source": "Competition rules - 99-point penalty for failure",
    })

    return steps
