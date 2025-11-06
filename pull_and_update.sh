#!/bin/bash
# Commands for the user to run on their WaCSim machine

cd ~/Desktop/WacsimCur/WaCSim

# Pull the latest changes from the Exp branch
git pull origin Exp

# If you get merge conflicts or need to force update:
# git fetch origin Exp
# git reset --hard origin/Exp

# Then reinstall WaCSim to pick up the changes
sudo pip3 install -e .

# Or if using pip without sudo:
# pip3 install -e .

# Now run the example again:
sudo wacsim examples/EdenTown/OddEven_CustomAlgo_Example/EdenTown_OddEven_config.yaml
