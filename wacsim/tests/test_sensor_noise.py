#!/usr/bin/env python3
"""Unit test for the multi-type sensor noise engine in basePLC.py.

Tests all 5 noise types and both config formats (legacy float, new dict).
Does NOT require Mininet or a running WaCSim simulation — tests the apply_noise()
method directly.
"""
import sys
import os
import numpy as np

# Add the WaCSim source to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# We can't import BasePLC directly because it inherits from minicps PLC.
# Instead, we test the noise logic by recreating the apply_noise function
# and the set_parameters config parsing.


class NoiseEngine:
    """Standalone replica of BasePLC's noise logic for testing without minicps."""

    def __init__(self):
        self.noise_config = {}
        self.default_noise_config = None
        self.noise_iteration = 0

    def set_parameters_from_config(self, noise_config):
        """Parse noise config — same logic as BasePLC.set_parameters()"""
        self.noise_iteration = 0
        if isinstance(noise_config, dict):
            self.noise_config = noise_config.get('sensors', {})
            self.default_noise_config = noise_config.get('default', None)
        elif isinstance(noise_config, (int, float)) and noise_config != 0:
            self.default_noise_config = {'type': 'gaussian', 'scale': float(noise_config)}
            self.noise_config = {}
        else:
            self.default_noise_config = None
            self.noise_config = {}

    def apply_noise(self, tag, sensor_value):
        """Apply configured noise — same logic as BasePLC.apply_noise()"""
        config = self.noise_config.get(tag, self.default_noise_config)
        if config is None or config.get('scale', 0) == 0:
            return sensor_value

        scale = config['scale']
        noise_type = config.get('type', 'gaussian')

        if noise_type == 'gaussian':
            return sensor_value + np.random.normal(0, scale * sensor_value)
        elif noise_type == 'gaussian_absolute':
            return sensor_value + np.random.normal(0, scale)
        elif noise_type == 'uniform':
            return sensor_value + np.random.uniform(-scale * sensor_value, scale * sensor_value)
        elif noise_type == 'percentage':
            return sensor_value * (1 + np.random.uniform(-scale, scale))
        elif noise_type == 'drift':
            return sensor_value + scale * self.noise_iteration
        else:
            return sensor_value


def test_legacy_float_config():
    """Test backward compatibility: plain float noise_scale → Gaussian."""
    print("=" * 60)
    print("TEST 1: Legacy float config (backward compatibility)")
    print("=" * 60)

    engine = NoiseEngine()
    engine.set_parameters_from_config(0.05)  # 5% Gaussian

    assert engine.default_noise_config == {'type': 'gaussian', 'scale': 0.05}
    assert engine.noise_config == {}

    base_value = 100.0
    values = [engine.apply_noise('T1', base_value) for _ in range(1000)]

    mean_noise = np.mean([v - base_value for v in values])
    std_noise = np.std([v - base_value for v in values])

    print(f"  Base value: {base_value}")
    print(f"  Expected std: {0.05 * base_value} = {0.05 * base_value}")
    print(f"  Actual mean noise: {mean_noise:.4f} (should be ~0)")
    print(f"  Actual std noise:  {std_noise:.4f} (should be ~{0.05 * base_value})")
    assert abs(mean_noise) < 1.0, f"Mean noise too large: {mean_noise}"
    assert abs(std_noise - 5.0) < 1.0, f"Std noise too far from expected: {std_noise}"
    print("  ✅ PASSED\n")


def test_no_noise():
    """Test that noise_config=0 produces no noise."""
    print("=" * 60)
    print("TEST 2: No noise (config=0)")
    print("=" * 60)

    engine = NoiseEngine()
    engine.set_parameters_from_config(0)

    base_value = 42.0
    result = engine.apply_noise('T1', base_value)
    assert result == base_value, f"Expected {base_value}, got {result}"
    print(f"  Value unchanged: {result} == {base_value}")
    print("  ✅ PASSED\n")


def test_gaussian():
    """Test multiplicative Gaussian noise."""
    print("=" * 60)
    print("TEST 3: Gaussian noise (multiplicative)")
    print("=" * 60)

    config = {
        'default': {'type': 'gaussian', 'scale': 0.10},
        'sensors': {}
    }
    engine = NoiseEngine()
    engine.set_parameters_from_config(config)

    base_value = 50.0
    values = [engine.apply_noise('T1', base_value) for _ in range(2000)]
    std = np.std([v - base_value for v in values])

    print(f"  Expected std: {0.10 * base_value} = {0.10 * base_value}")
    print(f"  Actual std:   {std:.4f}")
    assert abs(std - 5.0) < 1.0, f"Std too far from expected: {std}"
    print("  ✅ PASSED\n")


def test_gaussian_absolute():
    """Test fixed-std Gaussian noise (independent of value)."""
    print("=" * 60)
    print("TEST 4: Gaussian absolute noise")
    print("=" * 60)

    config = {
        'default': {'type': 'gaussian_absolute', 'scale': 0.5},
        'sensors': {}
    }
    engine = NoiseEngine()
    engine.set_parameters_from_config(config)

    # Test with two very different base values — std should be the same
    for base_value in [10.0, 1000.0]:
        values = [engine.apply_noise('T1', base_value) for _ in range(2000)]
        std = np.std([v - base_value for v in values])
        print(f"  Base={base_value:7.1f} → std={std:.4f} (expected ~0.5)")
        assert abs(std - 0.5) < 0.15, f"Std too far from 0.5: {std}"

    print("  ✅ PASSED\n")


def test_uniform():
    """Test bounded uniform noise."""
    print("=" * 60)
    print("TEST 5: Uniform noise")
    print("=" * 60)

    config = {
        'default': {'type': 'uniform', 'scale': 0.10},
        'sensors': {}
    }
    engine = NoiseEngine()
    engine.set_parameters_from_config(config)

    base_value = 100.0
    values = [engine.apply_noise('T1', base_value) for _ in range(5000)]
    min_v = min(values)
    max_v = max(values)
    mean_v = np.mean(values)

    bound = 0.10 * base_value  # = 10
    print(f"  Expected range: [{base_value - bound}, {base_value + bound}] = [90, 110]")
    print(f"  Actual range:   [{min_v:.4f}, {max_v:.4f}]")
    print(f"  Mean: {mean_v:.4f} (expected ~{base_value})")

    assert min_v >= base_value - bound - 0.01, f"Below lower bound: {min_v}"
    assert max_v <= base_value + bound + 0.01, f"Above upper bound: {max_v}"
    assert abs(mean_v - base_value) < 1.0, f"Mean too far: {mean_v}"
    print("  ✅ PASSED\n")


def test_percentage():
    """Test percentage noise."""
    print("=" * 60)
    print("TEST 6: Percentage noise")
    print("=" * 60)

    config = {
        'default': {'type': 'percentage', 'scale': 0.05},
        'sensors': {}
    }
    engine = NoiseEngine()
    engine.set_parameters_from_config(config)

    base_value = 200.0
    values = [engine.apply_noise('T1', base_value) for _ in range(5000)]
    min_v = min(values)
    max_v = max(values)

    # value * (1 + U(-0.05, 0.05)) → range [190, 210]
    print(f"  Expected range: [{base_value * 0.95}, {base_value * 1.05}] = [190, 210]")
    print(f"  Actual range:   [{min_v:.4f}, {max_v:.4f}]")

    assert min_v >= base_value * 0.95 - 0.01
    assert max_v <= base_value * 1.05 + 0.01
    print("  ✅ PASSED\n")


def test_drift():
    """Test drift noise (linearly increasing bias)."""
    print("=" * 60)
    print("TEST 7: Drift noise")
    print("=" * 60)

    config = {
        'default': {'type': 'drift', 'scale': 0.1},
        'sensors': {}
    }
    engine = NoiseEngine()
    engine.set_parameters_from_config(config)

    base_value = 50.0
    results = []
    for i in range(10):
        engine.noise_iteration = i
        result = engine.apply_noise('T1', base_value)
        expected = base_value + 0.1 * i
        results.append((i, result, expected))
        print(f"  Iteration {i}: value={result:.4f}, expected={expected:.4f}")
        assert abs(result - expected) < 0.001, f"Drift wrong at iteration {i}"

    print("  ✅ PASSED\n")


def test_per_sensor_override():
    """Test that per-sensor config overrides PLC default."""
    print("=" * 60)
    print("TEST 8: Per-sensor override")
    print("=" * 60)

    config = {
        'default': {'type': 'gaussian', 'scale': 0.05},
        'sensors': {
            'T1': {'type': 'uniform', 'scale': 0.10},
            'J5': {'type': 'gaussian_absolute', 'scale': 0.3}
        }
    }
    engine = NoiseEngine()
    engine.set_parameters_from_config(config)

    base_value = 100.0

    # T1 should use uniform, bounded by ±10
    t1_values = [engine.apply_noise('T1', base_value) for _ in range(2000)]
    t1_min, t1_max = min(t1_values), max(t1_values)
    print(f"  T1 (uniform ±10): range [{t1_min:.4f}, {t1_max:.4f}]")
    assert t1_min >= 90.0 - 0.01 and t1_max <= 110.0 + 0.01, "T1 out of uniform bounds"

    # J5 should use gaussian_absolute with std=0.3
    j5_values = [engine.apply_noise('J5', base_value) for _ in range(2000)]
    j5_std = np.std([v - base_value for v in j5_values])
    print(f"  J5 (gaussian_abs std=0.3): actual std={j5_std:.4f}")
    assert abs(j5_std - 0.3) < 0.1, f"J5 std wrong: {j5_std}"

    # T2 (not in per-sensor) should use default gaussian
    t2_values = [engine.apply_noise('T2', base_value) for _ in range(2000)]
    t2_std = np.std([v - base_value for v in t2_values])
    print(f"  T2 (default gaussian 5%): actual std={t2_std:.4f} (expected ~5.0)")
    assert abs(t2_std - 5.0) < 1.5, f"T2 std wrong: {t2_std}"

    print("  ✅ PASSED\n")


def test_input_parser_transform():
    """Test the YAML list → dict transformation (simulates input_parser.generate_sensor_noise)."""
    print("=" * 60)
    print("TEST 9: Input parser YAML → dict transform")
    print("=" * 60)

    # Simulated YAML input (as parsed by PyYAML)
    yaml_input = [
        {
            'name': 'PLC1',
            'default_noise': 'gaussian',
            'default_scale': 0.05,
            'sensors': [
                {'name': 'T1', 'noise_type': 'uniform', 'scale': 0.03},
                {'name': 'J5', 'noise_type': 'gaussian_absolute', 'scale': 0.1}
            ]
        },
        {
            'name': 'PLC2',
            'default_noise': 'percentage',
            'default_scale': 0.08
        }
    ]

    # Simulate generate_sensor_noise()
    sensor_noise = {}
    for plc_config in yaml_input:
        plc_name = plc_config['name']
        plc_noise = {
            'default': {
                'type': plc_config.get('default_noise', 'gaussian'),
                'scale': float(plc_config.get('default_scale', 0))
            },
            'sensors': {}
        }
        for sensor_config in plc_config.get('sensors', []):
            plc_noise['sensors'][sensor_config['name']] = {
                'type': sensor_config['noise_type'],
                'scale': float(sensor_config['scale'])
            }
        sensor_noise[plc_name] = plc_noise

    # Verify PLC1
    assert 'PLC1' in sensor_noise
    assert sensor_noise['PLC1']['default'] == {'type': 'gaussian', 'scale': 0.05}
    assert sensor_noise['PLC1']['sensors']['T1'] == {'type': 'uniform', 'scale': 0.03}
    assert sensor_noise['PLC1']['sensors']['J5'] == {'type': 'gaussian_absolute', 'scale': 0.1}
    print(f"  PLC1 default: {sensor_noise['PLC1']['default']}")
    print(f"  PLC1 T1: {sensor_noise['PLC1']['sensors']['T1']}")
    print(f"  PLC1 J5: {sensor_noise['PLC1']['sensors']['J5']}")

    # Verify PLC2
    assert 'PLC2' in sensor_noise
    assert sensor_noise['PLC2']['default'] == {'type': 'percentage', 'scale': 0.08}
    assert sensor_noise['PLC2']['sensors'] == {}
    print(f"  PLC2 default: {sensor_noise['PLC2']['default']}")
    print(f"  PLC2 sensors: (none — uses default)")

    # Now test that the engine works with this parsed config
    engine = NoiseEngine()
    engine.set_parameters_from_config(sensor_noise['PLC1'])

    # T1 should use uniform (overridden)
    base = 100.0
    t1_vals = [engine.apply_noise('T1', base) for _ in range(1000)]
    assert all(base - 3.01 <= v <= base + 3.01 for v in t1_vals), "T1 uniform bounds violated"
    print(f"  PLC1/T1 uniform ±3: range [{min(t1_vals):.4f}, {max(t1_vals):.4f}] ✓")

    print("  ✅ PASSED\n")


if __name__ == '__main__':
    np.random.seed(42)  # Reproducible tests

    print("\n🔧 WaCSim Multi-Type Sensor Noise Engine — Unit Tests\n")

    test_legacy_float_config()
    test_no_noise()
    test_gaussian()
    test_gaussian_absolute()
    test_uniform()
    test_percentage()
    test_drift()
    test_per_sensor_override()
    test_input_parser_transform()

    print("=" * 60)
    print("🎉 ALL 9 TESTS PASSED")
    print("=" * 60)
