-- Hubi Time - 0001_extensions
-- Habilita extensoes necessarias para geracao de UUID.
-- Seguro para reexecutar (idempotente).

create extension if not exists "pgcrypto";
