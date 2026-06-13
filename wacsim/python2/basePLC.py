import numpy as np
from minicps.devices import PLC


class BasePLC(PLC):

    def apply_noise(self, tag, sensor_value):
        """Apply configured noise to a sensor reading.

        Supports per-sensor noise configuration with multiple noise types.
        Falls back to PLC-level default if no per-sensor config exists.
        Returns the original value if no noise is configured.

        Supported noise types:
            - gaussian: Multiplicative Gaussian noise, std = scale * value
            - gaussian_absolute: Fixed std-dev Gaussian noise, std = scale
            - uniform: Bounded uniform noise, U(-scale*value, +scale*value)
            - percentage: Fixed percentage band, value * (1 + U(-scale, +scale))
            - drift: Linearly increasing bias, value + scale * iteration
        """
        # Look up per-sensor config first, then fall back to PLC default
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

    # Pulls a fresh value from the local DB and updates the local CPPPO
    def send_system_state(self):
        values = []
        # Send sensor values (may have configurable noise)
        for tag in self.sensors:
            # noinspection PyBroadException
            try:
                sensor_value = float(self.get(tag))
                values.append(self.apply_noise(tag, sensor_value))
            except Exception:
                self.logger.error("Exception trying to get the tag.")
                continue
        # Send actuator values (unaffected by noise)
        for tag in self.actuators:
            # noinspection PyBroadException
            try:
                values.append(self.get(tag))
            except Exception:
                self.logger.error("Exception trying to get the tag.")
                continue

        self.noise_iteration += 1
        self.send_multiple(self.tags, values, self.send_adddress)

    # Pulls a fresh value from the local DB and updates the local CPPPO
    def get_system_state(self):
        tag_values = {}  # Initialize dictionary to store tag-value pairs

        # Process sensor values (may have configurable noise)
        for tag in self.sensors:
            try:
                sensor_value = float(self.get(tag))
                tag_values[tag] = self.apply_noise(tag, sensor_value)
            except Exception:
                self.logger.error("Exception trying to get the sensor tag: %s", tag)
                continue

        # Process actuator values (unaffected by noise)
        for tag in self.actuators:
            try:
                tag_values[tag] = self.get(tag)
            except Exception:
                self.logger.error("Exception trying to get the actuator tag: %s", tag)
                continue

        return tag_values

    def set_parameters(self, sensors, actuators, values, send_address, noise_config, week_index=0):
        self.sensors = sensors
        self.actuators = actuators
        self.tags = self.sensors + self.actuators
        self.values = values
        self.send_adddress = send_address
        self.week_index = week_index
        self.cache_thread = None
        self.noise_iteration = 0

        # Parse noise configuration - supports both legacy (float) and new (dict) formats
        if isinstance(noise_config, dict):
            # New format: {'default': {'type': ..., 'scale': ...}, 'sensors': {'T1': {...}, ...}}
            self.noise_config = noise_config.get('sensors', {})
            self.default_noise_config = noise_config.get('default', None)
        elif isinstance(noise_config, (int, float)) and noise_config != 0:
            # Legacy format: single float noise_scale -> Gaussian for all sensors
            self.default_noise_config = {'type': 'gaussian', 'scale': float(noise_config)}
            self.noise_config = {}
        else:
            # No noise
            self.default_noise_config = None
            self.noise_config = {}