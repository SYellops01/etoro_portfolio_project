::This .txt file details the command line items to be run upfront to build the Docker container. 

::Required Installations
::VS Code Extensions - Python, Docker
::Docker Desktop Installation (https://docs.docker.com/get-started/get-docker/)


::for installing required virtual environment
pip install virtualenv
::navigate to root location
cd c:\Users\<USER_NAME>\

::create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate

::Navigate to infrastructure folder and build Docker container
cd infrastructure
docker compose up --build -d
