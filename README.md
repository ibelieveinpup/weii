# weii (weiibal fork)
**Enhanced Wii Balance Board Analyzer with Postural Metrics**  
*Fork of [skorokithakis/weii](https://github.com/skorokithakis/weii) with additional features*

<img src="https://upload.wikimedia.org/wikipedia/commons/thumb/3/3e/Wii_Balance_Board.svg/1200px-Wii_Balance_Board.svg.png" width="200" alt="Wii Balance Board">

## Features ✨
**Original Functionality:**
- Weight measurement using Nintendo Wii Balance Board
- Bluetooth connectivity management
- Basic command-line interface

**Extended Features (weiibal branch):**
- **Bilateral Weight Analysis** ⚖️  
  - Left/Right weight differential with percentage of total
  - Front/Back balance metrics with imbalance percentage
- **Enhanced Measurement Control** 🎛️  
  - `--samples`: Custom sample collection size (default: 200)
  - `--minlimit`: Adjust minimum weight threshold (kg)
- **Unit Conversion** 🔄  
  - Real-time `--units kg/lbs` conversion
- **Interactive Workflow** ⌨️  
  - Spacebar-triggered measurement start
- **Advanced Output** 📊  
  ```bash
  Total weight: 92.4 lbs
  Left Side: 1.8 lbs heavier (51.2% of total weight)
  Back: 4.3 lbs heavier (55.1% of total weight)

# Install from weiibal branch
pip install git+https://github.com/ibelieveinpup/weii.git@weiibal

# Verify installation
weii --version

# Standard measurement with bilateral metrics
weii --units lbs

# Custom sample size and sensitivity
weii --samples 300 --minlimit 15

# Full example with Bluetooth management
weii --samples 400 --units kg -d "00:1A:7D:DA:71:13"

# Measurement starts when SPACE is pressed
Press SPACE to begin measurement...

# Clone your fork
git clone https://github.com/ibelieveinpup/weii.git
cd weii

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install in editable mode
pip install -e .

# Add original repository
git remote add upstream https://github.com/skorokithakis/weii.git

# Fetch updates
git fetch upstream

# Merge safely
git checkout weiibal
git merge upstream/master

## Merging Upstream Updates 🔄
To sync with the original repository:

```bash
# Add original repository as upstream
git remote add upstream https://github.com/skorokithakis/weii.git

# Fetch latest changes
git fetch upstream

# Merge into your weiibal branch
git checkout weiibal
git merge upstream/master  # Original repo uses "master" branch

---

**Maintainer**: Steven (@ibelieveinpup)  
**Original Author**: Stavros Korokithakis ([@skorokithakis](https://github.com/skorokithakis))  
**License**: AGPL-3.0-or-later (inherited from upstream)
