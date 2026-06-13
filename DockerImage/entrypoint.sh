#!/bin/bash
# Start Open vSwitch service inside the container (required by Mininet)
service openvswitch-switch start

# Execute the user command (or bash)
exec "$@"
