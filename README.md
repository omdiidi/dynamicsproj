# ME 2030 Loop-the-Loop Prediction Tool

## How This Code Was Developed

This tool was developed for the ME 2030 Spring 2026 term project. The physics
model was built from first principles and verified against published literature
before implementation. AI-assisted development (Claude) was used for code
generation, with all physics independently verified.

## Dynamics Principles Used

1. **Work-Energy Theorem** — Energy conservation from release to loop top:

$$T_1 + V_1 + U_{NC} = T_2 + V_2$$

2. **Rotational Dynamics** — Rolling without slipping, kinetic energy via instant center (IC):

$$T = \tfrac{1}{2} I_{IC}\, \omega^2, \qquad I_G = \tfrac{2}{5} m R^2$$

3. **Two-Rail Contact Geometry** — Effective rolling radius correction (Bachman 1985, *Am. J. Phys.* 53(8), 765):

$$r_{eff} = \frac{R \cdot h_{offset}}{R + r_{rail}}, \qquad h_{offset} = \sqrt{(R + r_{rail})^2 - (s/2)^2}$$

4. **Newton's Second Law (Radial)** — Centripetal condition at loop top with $N = 0$:

$$\sum F_n = m a_n = \frac{m v^2}{\rho} \quad\Longrightarrow\quad v_{top}^2 = g R_c$$

5. **Rolling Resistance** — Energy dissipation as non-conservative work:

$$U_{NC} = \int \mathbf{F} \cdot d\mathbf{r} = C_{rr} \int N\, ds$$

## How to Run

### Locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

### On Render
Push to GitHub, connect repo in Render dashboard. The render.yaml configures
deployment automatically.

## Repository Structure

```
dynamics-claude/
├── app.py                       Streamlit dashboard (main entry point)
├── physics/                     Physics engine
│   ├── constants.py             Ball data, rail geometry, unit conversions
│   ├── geometry.py              Two-rail contact geometry (Bachman 1985)
│   ├── energy.py                Analytical energy-balance solver + waterfall
│   └── ode_model.py             scipy.solve_ivp simulation with events
├── docs/
│   ├── MEMO_RESPONSE.md         Memo writing reference (all four sections)
│   ├── APPENDIX.md              Full appendix (TOC, derivations, code listings)
│   └── project-info/            Original assignment materials (description,
│                                template, equation sheet)
├── .streamlit/config.toml       Streamlit theme + server config
├── render.yaml                  Render deployment blueprint
├── requirements.txt             Python dependencies
└── README.md                    This file
```

## Key Model Features

### Two-Rail Geometry Correction

The sphere rolls on two parallel 3mm-diameter cylindrical rails spaced 17mm apart (outside-to-outside, so center-to-center $s = 14$ mm). The effective rolling radius $r_{eff}$ is smaller than the ball radius $R$ because the contact points are elevated above the sphere's lowest point. The instant center of zero velocity lies along the line connecting the two contact points, at perpendicular distance $r_{eff}$ from the ball center. The rolling constraint becomes $\omega = v / r_{eff}$ instead of $v / R$, increasing the rotational kinetic energy fraction:

$$T = \tfrac{1}{2} m v^2 \left[ 1 + \tfrac{2}{5} \left(\tfrac{R}{r_{eff}}\right)^{2} \right] = \tfrac{1}{2} m v^2 \cdot KE_{factor}$$

For our balls, $KE_{factor}$ ranges from 1.89 (rubber) to 2.24 (steel), versus 1.4 on a flat surface — a 35–60% increase in required energy.

### Waterfall Breakdown

The prediction builds incrementally through 6 steps:

1. Frictionless sliding block: $h = \tfrac{5}{2} R$
2. Add rotational KE (flat surface): $h = \tfrac{27}{10} R$
3. Two-rail geometry correction (biggest single factor)
4. Rolling resistance (ramp + loop)
5. Transition losses at ramp-to-loop junction
6. Safety margin (rounded up to 0.1 in)

### ODE Simulation
Validates the analytical prediction by numerically integrating the equations
of motion with event detection for track departure, stalling, and loop completion.

## Connection to ME 2030 Course Material

The model uses these equations directly from the Dynamics Vocabulary sheet:

| Class Equation | Application in Model |
|---|---|
| $T = \tfrac{1}{2} m v_G^2 + \tfrac{1}{2} I_G \omega^2$ | Total KE of rolling sphere (modified for two-rail $r_{eff}$) |
| $a_n = v^2 / \rho$ | Centripetal condition at loop top ($\rho = R_c$) |
| $\mathbf{F} = m \mathbf{a}_G$ | Newton's 2nd law, radial direction in loop |
| $\sum M_{IC} = I_{IC}\, \alpha$ | Moment equation about instant center (rolling) |
| $I = \int r^2\, dm$ | $I_G = \tfrac{2}{5} m R^2$ for solid sphere |
| $U = \int \mathbf{F} \cdot d\mathbf{r}$ | Work done by rolling resistance along track |
| $T_1 + V_1 + U_{NC} = T_2 + V_2$ | Energy balance with non-conservative losses |
| $I_A = I_G + m d^2$ | Parallel axis theorem ($I_{IC} = I_G + m\, r_{eff}^2$) |
| $\mathbf{v}_A = \boldsymbol{\omega} \times \mathbf{r}_A$ | Rolling constraint via IC kinematics |

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
