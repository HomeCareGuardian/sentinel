-- Twin Postgres init (HA recorder + HCG core + readonly role).
CREATE DATABASE hcg_core;
CREATE USER hcg_admin WITH PASSWORD 'vch_hcg_password';
GRANT ALL PRIVILEGES ON DATABASE hcg_core TO hcg_admin;
CREATE USER hcg_readonly WITH PASSWORD 'vch_readonly_password';
GRANT CONNECT ON DATABASE homeassistant TO hcg_readonly;
GRANT CONNECT ON DATABASE hcg_core TO hcg_readonly;
