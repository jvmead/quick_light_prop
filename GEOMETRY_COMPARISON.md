# Geometry Comparison: Gap vs No-Gap

Comparing LAr gap configurations with **fixed physics** (realistic model).

## Run

```bash
python examples/geometry_comparison.py
```

## Test Configurations

1. **With Gap**: 1mm LAr gap between LC and WLS
2. **No Gap**: LC directly adjacent to WLS

**Fixed Parameters**:
- Full realistic physics (WLS absorption, dichroic, realistic QY, dispersion)
- Same random seed (42)
- 50,000 photons target, 500,000 max thrown

## Results

Generating... (script running)

### Efficiency Comparison

| Geometry | Efficiency | Notes |
|----------|------------|-------|
| With Gap | TBD | 1mm LAr spacing |
| No Gap | TBD | Direct contact |

### Expected Behavior

Gap and no-gap should show similar efficiency (~0.02% currently due to bug, ~1-2% after fix). The gap adds one extra optical interface but with similar refractive indices (n~1.23-1.65), so minimal TIR impact expected.

## Visualization

Plots will be generated at:
- `results/plots/geometry_comparison.png` - Efficiency comparison
- `results/plots/event_distribution_comparison.png` - Event type breakdown

## Outputs

- `results/geometry_comparison.csv` - Full simulation data
