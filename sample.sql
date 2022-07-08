
CREATE extension IF NOT EXISTS "uuid-ossp";

-- Table: public.books
CREATE TABLE IF NOT EXISTS public.books
(
    bookid uuid NOT NULL DEFAULT uuid_generate_v4(),
    title character varying COLLATE pg_catalog."default",
    book_info jsonb,
    CONSTRAINT books_pkey PRIMARY KEY (bookid)
)
WITH (
    OIDS = FALSE
)
TABLESPACE pg_default;

