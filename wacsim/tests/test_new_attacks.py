import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from wacsim.parser.config_parser import SchemaParser
from wacsim.network_attacks.noise_injection_netfilter_queue import NoiseInjectionNetfilterQueue
from schema import SchemaError

class TestNewAttacks(unittest.TestCase):
    
    def test_rogue_scada_schema(self):
        """Verify rogue_scada schema validation in config_parser."""
        attack_data = {
            'type': 'rogue_scada',
            'name': 'test_rogue',
            'target': 'PLC1',
            'trigger': {'type': 'time', 'start': 10, 'end': 20},
            'tags': [{'tag': 'ScadaCommand_P1', 'value': 0.0}]
        }
        
        schema = SchemaParser.network_attacks
        try:
            schema.validate(attack_data)
            valid = True
        except SchemaError as e:
            valid = False
            print("Schema validation failed:", e)
            
        self.assertTrue(valid)

    def test_noise_injection_schema(self):
        """Verify noise_injection schema validation in config_parser."""
        attack_data = {
            'type': 'noise_injection',
            'name': 'test_noise',
            'target': 'PLC2',
            'trigger': {'type': 'time', 'start': 15, 'end': 30},
            'tags': [{'tag': 'T1', 'noise_type': 'gaussian', 'scale': 0.2}]
        }
        
        schema = SchemaParser.network_attacks
        try:
            schema.validate(attack_data)
            valid = True
        except SchemaError as e:
            valid = False
            print("Schema validation failed:", e)
            
        self.assertTrue(valid)

    def test_tcp_rst_schema(self):
        """Verify tcp_rst schema validation in config_parser."""
        attack_data = {
            'type': 'tcp_rst',
            'name': 'test_rst',
            'target': 'PLC4',
            'trigger': {'type': 'time', 'start': 5, 'end': 10}
        }
        
        schema = SchemaParser.network_attacks
        try:
            schema.validate(attack_data)
            valid = True
        except SchemaError as e:
            valid = False
            print("Schema validation failed:", e)
            
        self.assertTrue(valid)

    def test_icmp_redirect_schema(self):
        """Verify icmp_redirect_mitm schema validation in config_parser."""
        attack_data = {
            'type': 'icmp_redirect_mitm',
            'name': 'test_redirect',
            'target': 'PLC2',
            'trigger': {'type': 'time', 'start': 10, 'end': 20},
            'tags': [{'tag': 'T1', 'value': 2.5}]
        }
        
        schema = SchemaParser.network_attacks
        try:
            schema.validate(attack_data)
            valid = True
        except SchemaError as e:
            valid = False
            print("Schema validation failed:", e)
            
        self.assertTrue(valid)

    @patch('wacsim.network_attacks.mitm_netfilter_queue_subprocess.PacketQueue.__init__', return_value=None)
    def test_noise_injection_math(self, mock_init):
        """Verify mathematical noise application logic in noise_injection_netfilter_queue."""
        # Manually create the object to avoid init looking for nonexistent YAML configurations
        queue = NoiseInjectionNetfilterQueue.__new__(NoiseInjectionNetfilterQueue)
        queue.logger = MagicMock()
        
        # 1. Test Gaussian noise
        tag_config = {'tag': 'T1', 'noise_type': 'gaussian', 'scale': 0.5}
        base_val = 10.0
        results = [queue.apply_noise(tag_config, base_val) for _ in range(100)]
        self.assertTrue(any(v != base_val for v in results))
        
        # 2. Test Absolute Gaussian noise
        tag_config_abs = {'tag': 'T1', 'noise_type': 'gaussian_absolute', 'scale': 2.0}
        results_abs = [queue.apply_noise(tag_config_abs, base_val) for _ in range(100)]
        self.assertTrue(any(v != base_val for v in results_abs))

        # 3. Test Uniform noise
        tag_config_uni = {'tag': 'T1', 'noise_type': 'uniform', 'scale': 0.1}
        results_uni = [queue.apply_noise(tag_config_uni, base_val) for _ in range(100)]
        for v in results_uni:
            self.assertTrue(9.0 <= v <= 11.0)
            
        # 4. Test Percentage noise
        tag_config_pct = {'tag': 'T1', 'noise_type': 'percentage', 'scale': 0.05}
        results_pct = [queue.apply_noise(tag_config_pct, base_val) for _ in range(100)]
        for v in results_pct:
            self.assertTrue(9.5 <= v <= 10.5)

        # 5. Test Drift noise
        tag_config_drift = {'tag': 'T1', 'noise_type': 'drift', 'scale': 0.2}
        queue.get_master_clock = MagicMock(return_value=5)
        val_drift = queue.apply_noise(tag_config_drift, base_val)
        self.assertAlmostEqual(val_drift, 11.0)

if __name__ == '__main__':
    unittest.main()
