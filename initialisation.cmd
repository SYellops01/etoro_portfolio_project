::This .txt file details the command line items to be run upfront to build the Docker container. 

::Required Installations/Setup
::VS Code Extensions - Python, Docker
::Docker Desktop Installation (https://docs.docker.com/get-started/get-docker/)
::Snowflake Trial Account (https://signup.snowflake.com/?trial=student&cloud=aws&region=eu-west-1&utm_source=handsonessentials&utm_campaign=uni-cmcw#)
::      Having set this up, run setup.sql in 'Snowflake'.
::DBT Trial Account (https://www.getdbt.com/signup)
::      Having set this up, configure with Snowflake account and set GitHub root folder to dbt/
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
