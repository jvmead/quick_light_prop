# Validation Scripts - Usage Guide

## Overview

Two separate validation scripts have been created to properly test the detector:

1. **Physics Model Validation** - Tests physics assumptions with fixed geometry
2. **Geometry Comparison** - Compares gap vs no-gap with fixed physics

## Scripts

### 1. Physics Model Validation

**File**: `examples/physics_model_validation.py`

**Purpose**: Test impact of physics approximations on detector performance

**Fixed Parameters**:
- Geometry: WITH LAr gap (1mm)
- Random seed: 42 (same for all tests)
- Photon counts: 10,000 target, 100,000 max thrown

**Variable Parameters** (6 tests):
1. **Baseline**: Full physics (WLS, dichroic, realistic QY, dispersion)
2. **No WLS Absorption**: Transparent materials (mu_a=0)
3. **No Dichroic**: Transparent mirror (R=0)
4. **Perfect QY**: Quantum yields = 1.0
5. **Poor QY**: Quantum yields = 0.5
6. **No Dispersion**: Constant refractive indices

**Usage**:
```bash
python examples/physics_model_validation.py
```

**Outputs**:
- `results/physics_model_validation.csv` - Combined results
- `results/plots/physics_model_comparison.png` - Efficiency bar chart

---

### 2. Geometry Comparison

**File**: `examples/geometry_comparison.py`

**Purpose**: Answer the design question - does the LAr gap matter?

**Fixed Parameters**:
- Physics: Full realistic model (same for both)
- Random seed: 42 (same for both)
- Photon counts: 50,000 target, 500,000 max thrown

**Variable Parameters** (2 tests):
1. **With Gap**: 1mm LAr gap between LC and WLS
2. **No Gap**: LC directly adjacent to WLS

**Usage**:
```bash
python examples/geometry_comparison.py
```

**Outputs**:
- `results/geometry_comparison.csv` - Combined results
- `results/plots/geometry_comparison.png` - Efficiency comparison
- `results/plots/event_distribution_comparison.png` - Event type breakdown

---

## Known Issues ⚠️

### Critical Bug: Photons Not Reaching LC/WLS

**Symptom**: Module produces much lower efficiency than notebooks
- Notebook: 1.24% efficiency
- Module: ~0.016% efficiency (80× lower!)

**Root Cause**: Photons are getting "lost" at the DM-WLS boundary instead of propagating through to LC.

**Evidence**:
- Notebook: 2,025 photons lost in LC, 88 in WLS ✓
- Module: 0 photons in LC, 0 in WLS ✗
- All photons get "lost_dm" or "lost_bulk"

**Impact**:
- Physics validation shows ALL configs with identical efficiency
- This is because photons never reach regions where physics varies (WLS, LC)
- Results are not meaningful until this bug is fixed

**Status**: Under investigation - see `INVESTIGATION_SUMMARY.md` for details

---

## Expected Behavior (After Bug Fix)

### Physics Model Validation
- **Different configs should show DIFFERENT efficiencies**
- No WLS absorption: Higher efficiency (less absorption losses)
- No dichroic: Different efficiency (less reflection back)
- Perfect QY: Higher efficiency (no non-radiative decay)
- Poor QY: Lower efficiency (more non-radiative decay)

### Geometry Comparison
- **Gap vs no-gap should show similar efficiency** (minor optical difference)
- Gap adds one extra interface (LC-gap, gap-WLS vs LC-WLS)
- Small refractive index difference may cause minor TIR changes

---

## Comparison to Original Notebooks

### Original Notebooks
- `photon_sim_analytic_gap_new.ipynb` - With LAr gap
- `photon_sim_analytic_no_gap_new.ipynb` - Without LAr gap

These notebooks have the CORRECT physics implementation and produce realistic results.

### Module Implementation
Currently has a boundary handling bug that prevents photons from reaching LC/WLS regions.

**Action Required**: Debug and fix the boundary transition logic in `photon_tracer/simulation.py`

---

## Directory Structure

```
trap_geom/
├── examples/
│   ├── physics_model_validation.py  ← NEW: Physics tests
│   ├── geometry_comparison.py       ← NEW: Geometry tests
│   ├── example_with_gap.py          ⚠️ Has geometry bug
│   ├── example_no_gap.py            ⚠️ Has geometry bug
│   ├── quick_demo.py                ⚠️ Has geometry bug
│   ├── physics_validation.py        ⚠️ Has geometry bug
│   └── physics_validation_fixed.py  ✓ Correct geometry
│
├── results/
│   ├── physics_model_validation.csv
│   ├── geometry_comparison.csv
│   └── plots/
│       ├── physics_model_comparison.png
│       ├── geometry_comparison.png
│       └── event_distribution_comparison.png
│
├── INVESTIGATION_SUMMARY.md        ← Detailed findings
└── VALIDATION_README.md            ← This file
```

---

## Next Steps

### For Users
1. **Read `INVESTIGATION_SUMMARY.md`** for full details of issues found
2. **Wait for bug fix** before running validation scripts for meaningful results
3. **Compare with notebook results** to verify correct behavior after fix

### For Developers
1. **Debug boundary handling** in `photon_tracer/simulation.py`
   - Add logging to trace volume transitions
   - Check `find_containing_volume()` at boundaries
   - Verify refraction doesn't point photons outside geometry

2. **Fix geometry bugs** in example scripts
   - Update `bulk_max` calculation (use `x_pos + bulk_x`)
   - Apply to: example_with_gap.py, example_no_gap.py, quick_demo.py, physics_validation.py

3. **Verify results** after fixes
   - Efficiency should increase to ~1-2% (like notebooks)
   - Physics variations should produce DIFFERENT results
   - Photons should reach LC and WLS regions

4. **Regenerate documentation**
   - Update validation plots
   - Update README with correct efficiency values
   - Update PHYSICS_VALIDATION.md with meaningful comparisons

---

## Questions?

See `INVESTIGATION_SUMMARY.md` for:
- Detailed root cause analysis
- Test results comparison table
- Step-by-step debug recommendations
- List of all files with issues

---

*Last Updated: 2026-01-13*
*Status: Scripts created, awaiting bug fix for meaningful results*
