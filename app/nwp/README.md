# Numerical Weather Prediction (NWP) Grid Processing (`app/nwp/`)

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-3776AB.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![NumPy](https://img.shields.io/badge/NumPy-1.26%2B-013243.svg?style=flat-square&logo=numpy&logoColor=white)](https://numpy.org/)
[![NWP Tests](https://img.shields.io/badge/NWP%20Tests-18%20Passing-brightgreen.svg?style=flat-square&logo=pytest&logoColor=white)](../../tests/)

**Deterministic 2D Bilinear Grid Interpolation, Zonal Aggregation & Multi-Model Divergence Analysis**

</div>

---

## 1. Scope & Atmospheric Models

The `app/nwp/` package provides high-performance deterministic processing for Numerical Weather Prediction grids covering the Indian subcontinent ($6^\circ\text{N}-38^\circ\text{N}, 68^\circ\text{E}-98^\circ\text{E}$):
- **NOAA GFS 0.25°**: Global Forecast System operational atmospheric grids.
- **ECMWF IFS 0.25°**: European Centre for Medium-Range Weather Forecasts prognostic fields.
- **Multi-Model Relative Divergence Ratio ($DR$)**: Evaluates forecast confidence across distinct NWP models.

---

## 2. Package Architecture

```text
app/nwp/
├── __init__.py                # Package exports (NWPEngine, types, readers, errors)
├── types.py                   # Pydantic v2 typed contracts (NWPGridArray, NWPPointResult, NWPPolygonResult, ModelDivergenceResult)
├── validation.py              # Grid validation, monotonicity checks & [0, 360] -> [-180, 180] longitude normalization
├── reader.py                  # GFS 0.25° and ECMWF IFS regional readers
├── interpolation.py           # Mathematically exact 2D Bilinear and Nearest-Neighbor interpolation
├── aggregation.py             # Polygon & MultiPolygon zonal extraction (mean, min, max, median, p90, sum)
├── divergence.py              # Multi-model spread and relative divergence ratio (DR) analysis
├── engine.py                  # NWPEngine high-level service class
└── errors.py                  # Typed NWP error taxonomy
```

---

## 3. Mathematical Foundations

### 3.1 2D Bilinear Spatial Interpolation
Evaluates atmospheric physical variables (Temperature, Precipitation, Wind vectors) at continuous coordinate points $(x, y)$ from 4 discrete grid vertices:

$$f(x, y) \approx \frac{1}{(x_2 - x_1)(y_2 - y_1)} \begin{bmatrix} x_2 - x & x - x_1 \end{bmatrix} \begin{bmatrix} f(Q_{11}) & f(Q_{12}) \\ f(Q_{21}) & f(Q_{22}) \end{bmatrix} \begin{bmatrix} y_2 - y \\ y - y_1 \end{bmatrix}$$

### 3.2 Multi-Model Relative Divergence Ratio ($DR$)
Quantifies atmospheric forecast uncertainty between GFS and ECMWF:

$$DR = \frac{\max(M_i) - \min(M_i)}{\mu(M) + \epsilon}$$

- **High Agreement**: $DR < 0.20 \implies$ High model confidence.
- **Moderate Divergence**: $0.20 \le DR \le 0.50 \implies$ Moderate uncertainty.
- **Significant Spread**: $DR > 0.50 \implies$ High atmospheric divergence / low confidence.
