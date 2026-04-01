-- Создание баз данных для сервисов
-- Этот скрипт выполняется при первом запуске PostgreSQL

-- База данных для auth-service
CREATE DATABASE auth_db;

-- База данных для task-service
CREATE DATABASE task_db;

-- Предоставление прав пользователю postgres
GRANT ALL PRIVILEGES ON DATABASE auth_db TO postgres;
GRANT ALL PRIVILEGES ON DATABASE task_db TO postgres;
