udo apt update
sudo apt install python3 python3-pip python3-venv ffmpeg
python3 -m venv radio_env
source radio_env/bin/activate
pip install -r requirements.txt
