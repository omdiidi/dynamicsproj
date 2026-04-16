"""
ODE-based simulation of a sphere rolling on a ramp + vertical circular loop.

Parameterizes the track as: ramp segment (arc length 0 to L_ramp) then
circular loop (arc length L_ramp to L_ramp + 2*pi*R_c).

Uses scipy.integrate.solve_ivp with terminal events:
  - Ball detaches from track (normal force N <= 0)
  - Ball stalls in the loop (v <= 0)
  - Ball completes the loop (s >= L_total)

Dynamics principles:
  - Newton's 2nd law (tangential: gravity + rolling resistance)
  - Newton's 2nd law (radial: centripetal condition for normal force)
  - Rolling constraint with effective radius from two-rail geometry
"""
import numpy as np
from scipy.integrate import solve_ivp
from .constants import G
from .geometry import compute_contact_geometry, compute_effective_loop_radius


def build_track(R_loop: float, theta_deg: float, h_release: float,
                h_offset: float, R_c: float):
    """
    Build a track geometry function.

    Track consists of:
    1. Straight ramp from release point to loop bottom
    2. Circular loop of CM radius R_c

    Returns:
        track_func: callable(s) -> (x, y, phi, kappa, segment)
        L_ramp: arc length of ramp
        L_total: total arc length
    """
    theta = np.radians(theta_deg)

    # Ramp length from height
    L_ramp = h_release / np.sin(theta)
    L_loop = 2 * np.pi * R_c
    L_total = L_ramp + L_loop

    # Starting position (top of ramp, ball center coordinates)
    x_start = -L_ramp * np.cos(theta)
    y_start = h_release + h_offset * np.cos(theta)

    # Loop center (ball center at bottom is at (0, h_offset))
    loop_cx = 0.0
    loop_cy = h_offset + R_c

    def track_func(s):
        s = max(0, min(s, L_total))  # clamp

        if s <= L_ramp:
            # On the ramp
            x = x_start + s * np.cos(theta)
            y = y_start - s * np.sin(theta)
            phi = -theta  # going downhill
            kappa = 0.0
            return x, y, phi, kappa, "ramp"
        else:
            # In the loop
            s_loop = s - L_ramp
            phi_loop = s_loop / R_c  # 0 at bottom, pi at top, 2pi back

            x = loop_cx + R_c * np.sin(phi_loop)
            y = loop_cy - R_c * np.cos(phi_loop)

            kappa = 1.0 / R_c
            return x, y, phi_loop, kappa, "loop"

    return track_func, L_ramp, L_total


def simulate(ball_radius: float, ball_mass: float, R_loop: float,
             theta_deg: float, h_release: float, C_rr: float,
             KE_factor: float, h_offset: float) -> dict:
    """
    Simulate the ball rolling down the ramp and through the loop.

    Returns dict with t, s, v, x, y, N arrays plus completion status.
    """
    R_c = R_loop - h_offset
    track, L_ramp, L_total = build_track(R_loop, theta_deg, h_release, h_offset, R_c)
    theta = np.radians(theta_deg)

    def ode(t, state):
        s, v = state
        if v <= 1e-10:
            v = 1e-10

        x, y, phi, kappa, segment = track(s)

        # Normal force
        if segment == "ramp":
            N = ball_mass * G * np.cos(theta)
        else:
            # N = mv^2/R_c + mg*cos(phi_loop)
            # Bottom (phi=0): N = mv^2/R_c + mg (correct)
            # Top (phi=pi): N = mv^2/R_c - mg (N=0 when v^2=gR_c)
            N = ball_mass * (v**2 / R_c + G * np.cos(phi))

        # Tangential acceleration
        if segment == "ramp":
            a_gravity = G * np.sin(theta)  # positive = downhill
        else:
            a_gravity = -G * np.sin(phi)  # negative when going up

        # Rolling resistance (opposes motion)
        a_rr = -C_rr * max(N, 0) / ball_mass * np.sign(v)

        # Divide by KE_factor for effective mass with rotation
        a = (a_gravity + a_rr) / KE_factor

        return [v, a]

    # Event: ball leaves track (N <= 0 in loop)
    def ball_leaves_track(t, state):
        s, v = state
        if s < L_ramp + 0.001:  # 1mm buffer past transition
            return 1.0
        x, y, phi, kappa, segment = track(s)
        N = ball_mass * (v**2 / R_c + G * np.cos(phi))
        return N

    ball_leaves_track.terminal = True
    ball_leaves_track.direction = -1

    # Event: ball stalls (v=0) in loop
    def ball_stalls(t, state):
        s, v = state
        if s < L_ramp:
            return 1.0
        return v

    ball_stalls.terminal = True
    ball_stalls.direction = -1

    # Event: ball completes loop
    def loop_complete(t, state):
        s, v = state
        return s - L_total

    loop_complete.terminal = True
    loop_complete.direction = 1

    # Estimate time and solve
    v_avg_est = max(np.sqrt(G * h_release), 0.1)
    t_max = max(3.0 * L_total / v_avg_est, 3.0)
    t_eval = np.linspace(0, t_max, 2000)

    sol = solve_ivp(ode, [0, t_max], [0.0, 1e-6], method='RK45',
                    t_eval=t_eval,
                    events=[ball_leaves_track, ball_stalls, loop_complete],
                    max_step=0.002, rtol=1e-6, atol=1e-8)

    # Extract results
    t_out = sol.t
    s_out = sol.y[0]
    v_out = sol.y[1]

    # Compute positions and normal forces
    positions = np.array([track(si)[:2] for si in s_out])
    x_out = positions[:, 0]
    y_out = positions[:, 1]

    N_out = np.zeros_like(t_out)
    for i, (si, vi) in enumerate(zip(s_out, v_out)):
        xi, yi, phi_i, kappa_i, seg_i = track(si)
        if seg_i == "ramp":
            N_out[i] = ball_mass * G * np.cos(theta)
        else:
            N_out[i] = ball_mass * (vi**2 / R_c + G * np.cos(phi_i))

    # Determine outcome (events: 0=leaves_track, 1=stalls, 2=loop_complete)
    completed = len(sol.t_events[2]) > 0
    failure_s = None
    failure_reason = None
    if len(sol.y_events[0]) > 0:
        failure_s = sol.y_events[0][0][0]
        failure_reason = "left_track"
    elif len(sol.y_events[1]) > 0:
        failure_s = sol.y_events[1][0][0]
        failure_reason = "stalled"

    return {
        "t": t_out,
        "s": s_out,
        "v": v_out,
        "x": x_out,
        "y": y_out,
        "N": N_out,
        "completed": completed,
        "failure_s": failure_s,
        "failure_reason": failure_reason,
        "L_ramp": L_ramp,
        "L_total": L_total,
        "track_func": track,
    }
