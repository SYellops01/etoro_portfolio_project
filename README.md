# etoro_portfolio_project
Building an end-to-end pipeline to identify all positions (including mirrors) that an individual holds in their portfolio. Dockerized infrastructure pulls this from API into minIO storage. Snowflake is used as the modern data warehouse, with project output a Streamlit-in-Snowflake application and Cortex Analyst agent. 
