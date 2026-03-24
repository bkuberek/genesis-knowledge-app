-- Create separate databases for Keycloak
-- Local dev uses keycloak_db, production (Coolify) uses knowledge_keycloak
CREATE DATABASE keycloak_db;
GRANT ALL PRIVILEGES ON DATABASE keycloak_db TO knowledge;

CREATE DATABASE knowledge_keycloak;
GRANT ALL PRIVILEGES ON DATABASE knowledge_keycloak TO knowledge;
