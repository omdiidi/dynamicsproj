# ME 2030 Loop-the-Loop Prediction Tool

## How This Code Was Developed

This tool was developed for the ME 2030 Spring 2026 term project. The physics
model was built from first principles and verified against published literature
before implementation. AI-assisted development (Claude) was used for code
generation, with all physics independently verified.

## Dynamics Principles Used

1. **Work-Energy Theorem** - Energy conservation from release to loop top
2. **Rotational Dynamics** - Rolling without slipping, moment of inertia I = 2/5 mR^2
3. **Two-Rail Contact Geometry** - Effective rolling radius correction for spheres
   on parallel cylindrical rails (Bachman 1985, Am. J. Phys. 53(8), 765)
4. **Newton's Second Law (Radial)** - Centripetal condition at loop top: N=0 gives v^2=gR_c
5. **Rolling Resistance** - Energy dissipation modeled with tunable C_rr per material

## How to Run

### Locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

### On Render
Push to GitHub, connect repo in Render dashboard. The render.yaml configures
deployment automatically.

## File Structure

- `app.py` - Streamlit dashboard (main entry point)
- `physics/constants.py` - Ball data, rail geometry, unit conversions
- `physics/geometry.py` - Two-rail contact geometry (Bachman 1985)
- `physics/energy.py` - Analytical energy-balance solver + waterfall breakdown
- `physics/ode_model.py` - ODE simulation with scipy solve_ivp event detection
- `.streamlit/config.toml` - Theme and server configuration
- `render.yaml` - Render deployment blueprint

## Key Model Features

### Two-Rail Geometry Correction
The sphere rolls on two parallel 3mm-diameter cylindrical rails spaced 17mm
apart (outside-to-outside). The effective rolling radius r_eff is smaller than
the ball radius R because the contact points are elevated above the sphere's
lowest point. This causes the ball to spin faster for a given translational
speed, requiring more energy (and thus more release height) than a flat surface.

### Waterfall Breakdown
The prediction builds incrementally through 6 steps:
1. Frictionless sliding block (h = 2.5R)
2. Add rotational KE (h = 2.7R)
3. Two-rail geometry correction (biggest single factor)
4. Rolling resistance
5. Transition losses at ramp-to-loop junction
6. Safety margin

### ODE Simulation
Validates the analytical prediction by numerically integrating the equations
of motion with event detection for track departure, stalling, and loop completion.

## Connection to ME 2030 Course Material

The model uses these equations directly from the Dynamics Vocabulary sheet:

| Class Equation | Application in Model |
|---|---|
| T = 1/2 mv^2_G + 1/2 I_G omega^2 | Total KE of rolling sphere (modified for two-rail r_eff) |
| a_n = v^2/rho | Centripetal condition at loop top (rho = R_c) |
| F = ma_G | Newton's 2nd law, radial direction in loop |
| Sum M_G = I_G alpha | Torque equation derives rolling constraint |
| I = integral r^2 dm | I_G = 2/5 mR^2 for solid sphere |
| U = integral F . dr | Work done by rolling resistance along track |
| T1 + V1 + U_NC = T2 + V2 | Energy balance with non-conservative losses |

Each equation is rendered in LaTeX in the app's "Dynamics Principles Applied" section
and in the waterfall derivation expander.

## References

- Bachman (1985), "Sphere rolling down a grooved track," Am. J. Phys. 53(8), 765
- West, Barrett & Vender (2024), "Deep in Galileo's Groove," The Physics Teacher 62(2), 104
- Wang et al. (2021), "Energy loss and jerk on the loop-the-loop," Am. J. Phys. 89(6), 583
- Bertran (2020), "A revised solution for a sphere rolling in a vertical loop"

## Assumptions and Limitations

1. Ball is a perfect solid uniform sphere (given in project description)
2. Rolling without slipping assumed throughout (may fail near loop top per Bertran 2020)
3. Rolling resistance coefficients estimated from literature, not measured for this track
4. Transition loss fraction is tunable, not derived from first principles
5. Track assumed to be a perfect circle (real track may have tolerances)
6. Air resistance neglected (justified at these scales and speeds)
7. Loop radius interpretation ambiguous - tool provides dropdown to switch assumptions
