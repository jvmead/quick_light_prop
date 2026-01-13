# Investigation Summary

## Issues Found

### 1. **Critical: Module produces much lower efficiency than notebooks**
- **Notebook**: 1.24% raw efficiency (124/10,000 target, 100,000 thrown)
- **Module**: 0.016% efficiency (79/50,000 target, 500,000 thrown)
- **Ratio**: ~80× lower efficiency

### 2. **Critical: Physics variations produce identical results**
- All physics configurations (baseline, no WLS, no dichroic, perfect QY, poor QY, no dispersion) produce **exactly 0.020% efficiency**
- This indicates photons are not reaching regions where these physics mechanisms matter

### 3. **Photons not reaching LC or WLS regions**

**Notebook event distribution:**
- Lost in bulk: 95,686
- **Lost in LC: 2,025** ✓
- **Lost in WLS: 88** ✓
- **Absorbed in WLS: 296** ✓
- Lost in DM: 1,620
- Lost in gap: 4
- Arrived: 124

**Module event distribution:**
- Lost in bulk: 473,265
- **Lost in LC: 0** ✗
- **Lost in WLS: 0** ✗
- **Absorbed in WLS: 0** ✗
- Lost in DM: 26,656
- Arrived: 79

**Key observation**: In the module, NO photons reach LC or WLS. They all get "lost" at DM or in bulk.

### 4. **No wavelength shifting observed**
- Notebook: Multiple wavelength transitions (128 nm → 420 nm → 490 nm)
- Module: All wavelength histories show only "128" (no shifts)
- This confirms photons never interact with WLS materials

## Root Cause Analysis

### Photons "lost_dm" - Boundary Handling Issue

When a photon reaches the DM-WLS boundary:
1. Photon is at boundary position (e.g., x=0.01003)
2. Code computes `test_point = position + direction * eps`
3. Calls `find_containing_volume(test_point)`
4. **Returns None** (outside all volumes) → photon marked as "lost_dm"

This suggests photons are exiting the geometry at the DM-WLS boundary instead of propagating through.

### Geometry Verification

Geometry setup is CORRECT:
- LC: x ∈ [0.000000, 0.010000]
- WLS: x ∈ [0.010000, 0.010003]  (3 μm thick)
- DM: x ∈ [0.010003, 0.010115]
- Bulk: x ∈ [0.010115, 0.510115]
- No gaps between volumes ✓

Test trace (manual): **Works correctly** (bulk → DM → WLS → LC → exit)

### Possible Causes

1. **Refraction changes direction unexpectedly**: After refraction at DM-WLS interface, new direction may point outside geometry
2. **Numerical precision**: Boundary calculations may have floating-point errors
3. **Volume ordering**: `find_containing_volume` returns first match; overlapping eps tolerances may cause issues
4. **Dichroic reflection**: Most photons may be reflecting back into bulk instead of transmitting

## What Was Fixed

### Geometry Bug in Example Scripts

**FOUND**: Most example scripts had incorrect bulk geometry:
```python
# WRONG (in example_with_gap.py, example_no_gap.py, quick_demo.py):
bulk_max = np.array([bulk_x, height, width])  # x=0.5

# CORRECT (should be):
bulk_max = np.array([x_pos + bulk_x, height, width])  # x=0.51+
```

This caused bulk to overlap with all other volumes!

**STATUS**: Not yet fixed in all files (to preserve current behavior for comparison)

## New Validation Structure

Created two proper validation scripts as requested:

### 1. `physics_model_validation.py`
- **Purpose**: Test physics assumptions with FIXED geometry
- **Geometry**: With LAr gap (constant)
- **Variables**: WLS absorption, dichroic, QY, dispersion
- **Tests**: 6 configurations

### 2. `geometry_comparison.py`
- **Purpose**: Compare gap vs no-gap with FIXED physics
- **Physics**: Full realistic model (constant)
- **Geometries**: With gap vs without gap
- **Tests**: 2 configurations

## Remaining Issues

### High Priority
1. **Debug boundary handling**: Why do photons get "lost_dm" instead of entering WLS?
2. **Compare simulation logic**: Line-by-line comparison of notebook vs module propagation
3. **Test with notebook code directly**: Run notebook simulation.py code in module to isolate issue

### Medium Priority
4. **Fix geometry bugs**: Update all example scripts with correct bulk_max
5. **Add detailed logging**: Instrument simulation to trace boundary crossings
6. **Verify refraction math**: Check if refracted directions are computed correctly

### Low Priority
7. **Optimize performance**: Module is slower than notebook (~30s vs ~9.5min for 500k photons)
8. **Add Fresnel reflections**: Currently not implemented (minor effect expected)

## Recommendations

### Immediate Actions
1. **Add debug logging** to `propagate_single_photon()` to trace:
   - Boundary positions
   - test_point calculations
   - Volume transitions
   - Direction changes after refraction

2. **Run notebook code directly** in module environment to confirm it produces correct results

3. **Compare refraction implementation** between notebook and module line-by-line

### Next Steps After Debug
1. Fix the boundary handling bug
2. Verify physics validation shows variation (not all identical)
3. Update all example scripts with correct geometry
4. Regenerate all validation plots
5. Update documentation with corrected results

## Files Modified/Created

### Created:
- `examples/physics_model_validation.py` - Physics validation (fixed geometry)
- `examples/geometry_comparison.py` - Geometry comparison (fixed physics)
- `diagnostic_test.py` - Diagnostic script
- `debug_single_photon.py` - Single photon trace test
- `INVESTIGATION_SUMMARY.md` - This file

### Issues Found In:
- `examples/example_with_gap.py` - Wrong bulk_max (line 72)
- `examples/example_no_gap.py` - Wrong bulk_max (line 66)
- `examples/quick_demo.py` - Wrong bulk_max (line 54)
- `examples/physics_validation.py` - Wrong bulk_max (line 85)

### Correct:
- `examples/physics_validation_fixed.py` - Correct geometry ✓

## Test Results Summary

| Script | Geometry | Efficiency | Notes |
|--------|----------|------------|-------|
| Notebook (gap) | Correct | 1.24% | Many photons reach LC/WLS ✓ |
| example_with_gap.py | **WRONG** | 0.016% | NO photons in LC/WLS ✗ |
| physics_validation_fixed.py | Correct | 0.020% | NO photons in LC/WLS ✗ |
| diagnostic_test.py | Correct | 0.000% | NO photons in LC/WLS ✗ |

**Conclusion**: Even with correct geometry, module has the boundary handling bug.

---

*Investigation Date: 2026-01-13*
*Status: In Progress - Boundary handling bug identified but not yet fixed*
