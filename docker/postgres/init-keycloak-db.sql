-- Create Keycloak databases during PostgreSQL initialization.
-- Runs as POSTGRES_USER who automatically owns each created database.
-- Local dev uses keycloak_db; production (Coolify) uses knowledge_keycloak.
CREATE DATABASE keycloak_db;
CREATE DATABASE knowledge_keycloak;
