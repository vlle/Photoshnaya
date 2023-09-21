--
-- PostgreSQL database cluster dump
--

SET default_transaction_read_only = off;

SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;

--
-- Drop databases (except postgres and template1)
--





--
-- Drop roles
--

DROP ROLE postgres;


--
-- Roles
--

CREATE ROLE postgres;
ALTER ROLE postgres WITH SUPERUSER INHERIT CREATEROLE CREATEDB LOGIN REPLICATION BYPASSRLS PASSWORD 'SCRAM-SHA-256$4096:h3s8rRVzm8iLgzcxxM9JIQ==$HgzBXticjcwwlyfS67zYg86Ng+7n9ikQLkzC/jlaXqU=:8ax2YjaxXz1gMdu3zc4n5dxMs7yFR0QqO/Zt+NfCgEM=';

--
-- User Configurations
--








--
-- Databases
--

--
-- Database "template1" dump
--

--
-- PostgreSQL database dump
--

-- Dumped from database version 15.3 (Debian 15.3-1.pgdg120+1)
-- Dumped by pg_dump version 15.3 (Debian 15.3-1.pgdg120+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

UPDATE pg_catalog.pg_database SET datistemplate = false WHERE datname = 'template1';
DROP DATABASE template1;
--
-- Name: template1; Type: DATABASE; Schema: -; Owner: postgres
--

CREATE DATABASE template1 WITH TEMPLATE = template0 ENCODING = 'UTF8' LOCALE_PROVIDER = libc LOCALE = 'en_US.utf8';


ALTER DATABASE template1 OWNER TO postgres;

\connect template1

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: DATABASE template1; Type: COMMENT; Schema: -; Owner: postgres
--

COMMENT ON DATABASE template1 IS 'default template for new databases';


--
-- Name: template1; Type: DATABASE PROPERTIES; Schema: -; Owner: postgres
--

ALTER DATABASE template1 IS_TEMPLATE = true;


\connect template1

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: DATABASE template1; Type: ACL; Schema: -; Owner: postgres
--

REVOKE CONNECT,TEMPORARY ON DATABASE template1 FROM PUBLIC;
GRANT CONNECT ON DATABASE template1 TO PUBLIC;


--
-- PostgreSQL database dump complete
--

--
-- Database "postgres" dump
--

--
-- PostgreSQL database dump
--

-- Dumped from database version 15.3 (Debian 15.3-1.pgdg120+1)
-- Dumped by pg_dump version 15.3 (Debian 15.3-1.pgdg120+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

DROP DATABASE postgres;
--
-- Name: postgres; Type: DATABASE; Schema: -; Owner: postgres
--

CREATE DATABASE postgres WITH TEMPLATE = template0 ENCODING = 'UTF8' LOCALE_PROVIDER = libc LOCALE = 'en_US.utf8';


ALTER DATABASE postgres OWNER TO postgres;

\connect postgres

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: DATABASE postgres; Type: COMMENT; Schema: -; Owner: postgres
--

COMMENT ON DATABASE postgres IS 'default administrative connection database';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: contest; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.contest (
    id integer NOT NULL,
    contest_name character varying NOT NULL,
    contest_duration_sec integer NOT NULL,
    link_to_results character varying,
    created_date timestamp with time zone DEFAULT now() NOT NULL,
    group_id integer NOT NULL
);


ALTER TABLE public.contest OWNER TO postgres;

--
-- Name: contest_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.contest_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.contest_id_seq OWNER TO postgres;

--
-- Name: contest_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.contest_id_seq OWNED BY public.contest.id;


--
-- Name: contest_participant; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.contest_participant (
    contest_id integer NOT NULL,
    user_id integer NOT NULL
);


ALTER TABLE public.contest_participant OWNER TO postgres;

--
-- Name: contest_user; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.contest_user (
    contest_id integer NOT NULL,
    user_id integer NOT NULL
);


ALTER TABLE public.contest_user OWNER TO postgres;

--
-- Name: contest_winner; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.contest_winner (
    contest_id integer NOT NULL,
    user_id integer NOT NULL
);


ALTER TABLE public.contest_winner OWNER TO postgres;

--
-- Name: group; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public."group" (
    id integer NOT NULL,
    name character varying NOT NULL,
    telegram_id bigint NOT NULL,
    vote_in_progress boolean NOT NULL,
    created_date timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public."group" OWNER TO postgres;

--
-- Name: group_admin; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.group_admin (
    user_id integer NOT NULL,
    group_id integer NOT NULL
);


ALTER TABLE public.group_admin OWNER TO postgres;

--
-- Name: group_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.group_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.group_id_seq OWNER TO postgres;

--
-- Name: group_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.group_id_seq OWNED BY public."group".id;


--
-- Name: group_photo; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.group_photo (
    photo_id integer NOT NULL,
    group_id integer NOT NULL
);


ALTER TABLE public.group_photo OWNER TO postgres;

--
-- Name: group_user; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.group_user (
    user_id integer NOT NULL,
    group_id integer NOT NULL
);


ALTER TABLE public.group_user OWNER TO postgres;

--
-- Name: photo; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.photo (
    id integer NOT NULL,
    file_id character varying NOT NULL,
    telegram_type character varying(15) NOT NULL,
    user_id integer NOT NULL
);


ALTER TABLE public.photo OWNER TO postgres;

--
-- Name: photo_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.photo_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.photo_id_seq OWNER TO postgres;

--
-- Name: photo_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.photo_id_seq OWNED BY public.photo.id;


--
-- Name: photo_like; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.photo_like (
    user_id integer NOT NULL,
    photo_id integer NOT NULL
);


ALTER TABLE public.photo_like OWNER TO postgres;

--
-- Name: tmp_photo_like; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tmp_photo_like (
    user_id integer NOT NULL,
    photo_id integer NOT NULL
);


ALTER TABLE public.tmp_photo_like OWNER TO postgres;

--
-- Name: user; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public."user" (
    id integer NOT NULL,
    name character varying(30) NOT NULL,
    full_name character varying,
    telegram_id bigint NOT NULL,
    created_date timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public."user" OWNER TO postgres;

--
-- Name: user_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_id_seq OWNER TO postgres;

--
-- Name: user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.user_id_seq OWNED BY public."user".id;


--
-- Name: contest id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contest ALTER COLUMN id SET DEFAULT nextval('public.contest_id_seq'::regclass);


--
-- Name: group id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."group" ALTER COLUMN id SET DEFAULT nextval('public.group_id_seq'::regclass);


--
-- Name: photo id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.photo ALTER COLUMN id SET DEFAULT nextval('public.photo_id_seq'::regclass);


--
-- Name: user id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."user" ALTER COLUMN id SET DEFAULT nextval('public.user_id_seq'::regclass);


--
-- Data for Name: contest; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.contest (id, contest_name, contest_duration_sec, link_to_results, created_date, group_id) FROM stdin;
1	-1	-1	\N	2023-08-31 13:57:49.584196+00	1
2	#еда	1694584800	\N	2023-08-31 13:58:09.103499+00	1
\.


--
-- Data for Name: contest_participant; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.contest_participant (contest_id, user_id) FROM stdin;
2	1
2	2
\.


--
-- Data for Name: contest_user; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.contest_user (contest_id, user_id) FROM stdin;
\.


--
-- Data for Name: contest_winner; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.contest_winner (contest_id, user_id) FROM stdin;
\.


--
-- Data for Name: group; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public."group" (id, name, telegram_id, vote_in_progress, created_date) FROM stdin;
1	Artemii & testPhotosh, Сергей	-949286797	t	2023-08-31 13:57:49.584196+00
\.


--
-- Data for Name: group_admin; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.group_admin (user_id, group_id) FROM stdin;
1	1
\.


--
-- Data for Name: group_photo; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.group_photo (photo_id, group_id) FROM stdin;
1	1
2	1
\.


--
-- Data for Name: group_user; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.group_user (user_id, group_id) FROM stdin;
1	1
2	1
\.


--
-- Data for Name: photo; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.photo (id, file_id, telegram_type, user_id) FROM stdin;
1	AgACAgIAAxkBAAIEhWTwnIUlWyTh3O21y00hsQlK_tiwAAKgzjEbJB-JS4bJbHE0dpEVAQADAgADeQADMAQ	photo	1
2	AgACAgIAAxkBAAIEh2TwnJBFRm6Ho7QTxX1utgABS08rGwACoc4xGyQfiUumtempAyl6twEAAwIAA3kAAzAE	photo	2
\.


--
-- Data for Name: photo_like; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.photo_like (user_id, photo_id) FROM stdin;
\.


--
-- Data for Name: tmp_photo_like; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.tmp_photo_like (user_id, photo_id) FROM stdin;
\.


--
-- Data for Name: user; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public."user" (id, name, full_name, telegram_id, created_date) FROM stdin;
1	mtrrb	Artemii Kulikov	1919118841	2023-08-31 13:57:49.600982+00
2	voltv	Ssa	5074707989	2023-08-31 13:58:40.545517+00
\.


--
-- Name: contest_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.contest_id_seq', 2, true);


--
-- Name: group_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.group_id_seq', 1, true);


--
-- Name: photo_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.photo_id_seq', 2, true);


--
-- Name: user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.user_id_seq', 2, true);


--
-- Name: contest_participant contest_participant_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contest_participant
    ADD CONSTRAINT contest_participant_pkey PRIMARY KEY (contest_id, user_id);


--
-- Name: contest contest_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contest
    ADD CONSTRAINT contest_pkey PRIMARY KEY (id);


--
-- Name: contest_user contest_user_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contest_user
    ADD CONSTRAINT contest_user_pkey PRIMARY KEY (contest_id, user_id);


--
-- Name: contest_winner contest_winner_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contest_winner
    ADD CONSTRAINT contest_winner_pkey PRIMARY KEY (contest_id, user_id);


--
-- Name: group_admin group_admin_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_admin
    ADD CONSTRAINT group_admin_pkey PRIMARY KEY (user_id, group_id);


--
-- Name: group_photo group_photo_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_photo
    ADD CONSTRAINT group_photo_pkey PRIMARY KEY (photo_id, group_id);


--
-- Name: group group_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."group"
    ADD CONSTRAINT group_pkey PRIMARY KEY (id);


--
-- Name: group_user group_user_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_user
    ADD CONSTRAINT group_user_pkey PRIMARY KEY (user_id, group_id);


--
-- Name: photo_like photo_like_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.photo_like
    ADD CONSTRAINT photo_like_pkey PRIMARY KEY (user_id, photo_id);


--
-- Name: photo photo_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.photo
    ADD CONSTRAINT photo_pkey PRIMARY KEY (id);


--
-- Name: tmp_photo_like tmp_photo_like_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tmp_photo_like
    ADD CONSTRAINT tmp_photo_like_pkey PRIMARY KEY (user_id, photo_id);


--
-- Name: user user_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_pkey PRIMARY KEY (id);


--
-- Name: contest contest_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contest
    ADD CONSTRAINT contest_group_id_fkey FOREIGN KEY (group_id) REFERENCES public."group"(id);


--
-- Name: contest_participant contest_participant_contest_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contest_participant
    ADD CONSTRAINT contest_participant_contest_id_fkey FOREIGN KEY (contest_id) REFERENCES public.contest(id);


--
-- Name: contest_participant contest_participant_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contest_participant
    ADD CONSTRAINT contest_participant_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: contest_user contest_user_contest_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contest_user
    ADD CONSTRAINT contest_user_contest_id_fkey FOREIGN KEY (contest_id) REFERENCES public.contest(id);


--
-- Name: contest_user contest_user_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contest_user
    ADD CONSTRAINT contest_user_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: contest_winner contest_winner_contest_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contest_winner
    ADD CONSTRAINT contest_winner_contest_id_fkey FOREIGN KEY (contest_id) REFERENCES public.contest(id);


--
-- Name: contest_winner contest_winner_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contest_winner
    ADD CONSTRAINT contest_winner_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: group_admin group_admin_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_admin
    ADD CONSTRAINT group_admin_group_id_fkey FOREIGN KEY (group_id) REFERENCES public."group"(id);


--
-- Name: group_admin group_admin_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_admin
    ADD CONSTRAINT group_admin_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: group_photo group_photo_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_photo
    ADD CONSTRAINT group_photo_group_id_fkey FOREIGN KEY (group_id) REFERENCES public."group"(id);


--
-- Name: group_photo group_photo_photo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_photo
    ADD CONSTRAINT group_photo_photo_id_fkey FOREIGN KEY (photo_id) REFERENCES public.photo(id);


--
-- Name: group_user group_user_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_user
    ADD CONSTRAINT group_user_group_id_fkey FOREIGN KEY (group_id) REFERENCES public."group"(id);


--
-- Name: group_user group_user_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_user
    ADD CONSTRAINT group_user_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: photo_like photo_like_photo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.photo_like
    ADD CONSTRAINT photo_like_photo_id_fkey FOREIGN KEY (photo_id) REFERENCES public.photo(id);


--
-- Name: photo_like photo_like_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.photo_like
    ADD CONSTRAINT photo_like_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: photo photo_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.photo
    ADD CONSTRAINT photo_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: tmp_photo_like tmp_photo_like_photo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tmp_photo_like
    ADD CONSTRAINT tmp_photo_like_photo_id_fkey FOREIGN KEY (photo_id) REFERENCES public.photo(id);


--
-- Name: tmp_photo_like tmp_photo_like_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tmp_photo_like
    ADD CONSTRAINT tmp_photo_like_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- PostgreSQL database dump complete
--

--
-- PostgreSQL database cluster dump complete
--
