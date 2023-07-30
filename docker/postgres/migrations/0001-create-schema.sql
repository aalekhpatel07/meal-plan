SELECT 'CREATE DATABASE mealplan'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'mealplan')\gexec

SET search_path TO public;

CREATE TABLE IF NOT EXISTS recipes
(
  id integer primary key,
  payload jsonb not null default '{}'::jsonb
);
