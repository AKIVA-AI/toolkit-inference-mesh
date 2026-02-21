
# Toolkit fork note

This documentation was authored upstream for Parallax. In the Toolkit-branded fork:

- Use `toolkit-mesh` as the primary CLI command.
- `parallax` remains available as an alias, so existing upstream commands still work unchanged.
- Upstream clone/install links may point to `GradientHQ/parallax`; for this fork, install from this repository folder.

## Installation

### Prerequisites
- Python>=3.11.0,<3.14.0
- Ubuntu-24.04 for Blackwell GPUs

Below are installation methods for different operating systems.

|  Operating System  |  Windows App  |  From Source | Docker |
|:-------------|:----------------------------:|:----------------------------:|:----------------------------:|
|Windows       | âœ…ï¸ | Not recommended | Not recommended |
|Linux | âŒï¸ | âœ…ï¸ | âœ…ï¸ |
|macOS | âŒï¸ | âœ…ï¸ | âŒï¸ |

### From Source
#### For Linux/WSL (GPU):
Note: If you are using DGX Spark, please refer to the Docker installation section
```sh
git clone https://github.com/GradientHQ/parallax.git
cd parallax
pip install -e '.[gpu]'
```

#### For macOS (Apple silicon):

We recommend macOS users to create an isolated Python virtual environment before installation.

```sh
git clone https://github.com/GradientHQ/parallax.git
cd parallax

# Enter Python virtual environment
python3 -m venv ./venv
source ./venv/bin/activate

pip install -e '.[mac]'
```

Next time to re-activate this virtual environment, run ```source ./venv/bin/activate```.

#### Extra step for development:
```sh
pip install -e '.[dev]'
```

### Windows Application
[Click here](https://github.com/GradientHQ/parallax_win_cli/releases/latest/download/Parallax_Win_Setup.exe) to get latest Windows installer.

After installing .exe, right click Windows start button and click ```Windows Terminal(Admin)``` to start a Powershell console as administrator.

â— Make sure you open your terminal with administrator privileges.
<details>
<summary>Ways to run Windows Terminal as administrator</summary>

- Start menu: Rightâ€‘click Start and choose "Windows Terminal (Admin)", or search "Windows Terminal", rightâ€‘click the result, and select "Run as administrator".
- Run dialog: Press Win+R â†’ type `wt` â†’ press Ctrl+Shift+Enter.
- Task Manager: Press Ctrl+Shift+Esc â†’ File â†’ Run new task â†’ enter `wt` â†’ check "Create this task with administrator privileges".
- File Explorer: Open the target folder â†’ hold Ctrl+Shift â†’ rightâ€‘click in the folder â†’ select "Open in Terminal".
</details>
<br>

Start Windows dependencies installation by simply typing this command in console:
```sh
parallax install
```

Installation process may take around 30 minutes.

To see a description of all Parallax Windows configurations you can do:
```sh
parallax --help
```

### Docker
For Linux+GPU devices, Parallax provides a docker environment for quick setup. Choose the docker image according to the device's GPU architechture.

|  GPU Architecture  |  GPU Series  | Image Pull Command |
|:-------------|:----------------------------|:----------------------------|
|Blackwell/Ampere/Hopper| RTX50 series/RTX40 series/B100/B200/A100/H100... |```docker pull gradientservice/parallax:latest```|
|DGX Spark | GB10 |```docker pull gradientservice/parallax:latest-spark```|

Run a docker container as below. Please note that generally the argument ```--gpus all``` is necessary for the docker to run on GPUs.
```sh
# For Blackwell/Ampere/Hopper
docker run -it --gpus all --network host gradientservice/parallax:latest bash
# For DGX Spark
docker run -it --gpus all --network host gradientservice/parallax:latest-spark bash
```
The container starts under parallax workspace and you should be able to run parallax directly.

### Uninstalling Parallax

For macOS or Linux, if you've installed Parallax via pip and want to uninstall it, you can use the following command:

```sh
pip uninstall parallax
```

For Docker installations, remove Parallax images and containers using standard Docker commands:

```sh
docker ps -a               # List running containers
docker stop <container_id> # Stop running containers
docker rm <container_id>   # Remove stopped containers
docker images              # List Docker images
docker rmi <image_id>      # Remove Parallax images
```

For Windows, simply go to Control Panel â†’ Programs â†’ Uninstall a program, find "Gradient" in the list, and uninstall it.


