--
-- PostgreSQL database dump
--

-- Dumped from database version 16.4
-- Dumped by pg_dump version 16.4

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
-- Name: btree_gist; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS btree_gist WITH SCHEMA public;


--
-- Name: EXTENSION btree_gist; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION btree_gist IS 'support for indexing common datatypes in GiST';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: healthcare
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO healthcare;

--
-- Name: appointment_status_history; Type: TABLE; Schema: public; Owner: healthcare
--

CREATE TABLE public.appointment_status_history (
    id integer NOT NULL,
    appointment_id integer NOT NULL,
    field character varying(32) NOT NULL,
    from_value character varying(64),
    to_value character varying(64) NOT NULL,
    reason character varying(500),
    source character varying(32) NOT NULL,
    created_at timestamp with time zone NOT NULL
);


ALTER TABLE public.appointment_status_history OWNER TO healthcare;

--
-- Name: appointment_status_history_id_seq; Type: SEQUENCE; Schema: public; Owner: healthcare
--

CREATE SEQUENCE public.appointment_status_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.appointment_status_history_id_seq OWNER TO healthcare;

--
-- Name: appointment_status_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: healthcare
--

ALTER SEQUENCE public.appointment_status_history_id_seq OWNED BY public.appointment_status_history.id;


--
-- Name: appointment_types; Type: TABLE; Schema: public; Owner: healthcare
--

CREATE TABLE public.appointment_types (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    description text,
    duration_minutes integer NOT NULL,
    buffer_minutes integer NOT NULL,
    fee_override numeric(12,2),
    specialty_id integer,
    doctor_id integer,
    is_active boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_appointment_types_buffer_non_negative CHECK ((buffer_minutes >= 0)),
    CONSTRAINT ck_appointment_types_duration_positive CHECK ((duration_minutes > 0))
);


ALTER TABLE public.appointment_types OWNER TO healthcare;

--
-- Name: appointment_types_id_seq; Type: SEQUENCE; Schema: public; Owner: healthcare
--

CREATE SEQUENCE public.appointment_types_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.appointment_types_id_seq OWNER TO healthcare;

--
-- Name: appointment_types_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: healthcare
--

ALTER SEQUENCE public.appointment_types_id_seq OWNED BY public.appointment_types.id;


--
-- Name: appointments; Type: TABLE; Schema: public; Owner: healthcare
--

CREATE TABLE public.appointments (
    id integer NOT NULL,
    booking_reference character varying(16) NOT NULL,
    patient_id integer NOT NULL,
    doctor_id integer NOT NULL,
    appointment_type_id integer NOT NULL,
    start_time timestamp with time zone NOT NULL,
    end_time timestamp with time zone NOT NULL,
    end_with_buffer timestamp with time zone NOT NULL,
    status character varying(32) NOT NULL,
    status_reason character varying(500),
    check_in_status character varying(32) NOT NULL,
    erp_booking_id character varying(64),
    reason_for_visit character varying(1000),
    fee_amount numeric(12,2) NOT NULL,
    currency character varying(3) NOT NULL,
    cancelled_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_appointments_buffer_range CHECK ((end_with_buffer >= end_time)),
    CONSTRAINT ck_appointments_time_range CHECK ((end_time > start_time))
);


ALTER TABLE public.appointments OWNER TO healthcare;

--
-- Name: appointments_id_seq; Type: SEQUENCE; Schema: public; Owner: healthcare
--

CREATE SEQUENCE public.appointments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.appointments_id_seq OWNER TO healthcare;

--
-- Name: appointments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: healthcare
--

ALTER SEQUENCE public.appointments_id_seq OWNED BY public.appointments.id;


--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: healthcare
--

CREATE TABLE public.audit_logs (
    id bigint NOT NULL,
    actor_id integer,
    actor_type character varying(32) NOT NULL,
    action character varying(64) NOT NULL,
    entity_type character varying(64) NOT NULL,
    entity_id character varying(64),
    details jsonb,
    request_id character varying(64),
    created_at timestamp with time zone NOT NULL
);


ALTER TABLE public.audit_logs OWNER TO healthcare;

--
-- Name: audit_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: healthcare
--

CREATE SEQUENCE public.audit_logs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.audit_logs_id_seq OWNER TO healthcare;

--
-- Name: audit_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: healthcare
--

ALTER SEQUENCE public.audit_logs_id_seq OWNED BY public.audit_logs.id;


--
-- Name: departments; Type: TABLE; Schema: public; Owner: healthcare
--

CREATE TABLE public.departments (
    id integer NOT NULL,
    hospital_id integer NOT NULL,
    specialty_id integer NOT NULL,
    name character varying(150) NOT NULL,
    description text,
    is_active boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.departments OWNER TO healthcare;

--
-- Name: departments_id_seq; Type: SEQUENCE; Schema: public; Owner: healthcare
--

CREATE SEQUENCE public.departments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.departments_id_seq OWNER TO healthcare;

--
-- Name: departments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: healthcare
--

ALTER SEQUENCE public.departments_id_seq OWNED BY public.departments.id;


--
-- Name: doctor_schedules; Type: TABLE; Schema: public; Owner: healthcare
--

CREATE TABLE public.doctor_schedules (
    id integer NOT NULL,
    doctor_id integer NOT NULL,
    start_time timestamp with time zone NOT NULL,
    end_time timestamp with time zone NOT NULL,
    max_appointments integer,
    is_available boolean NOT NULL,
    source character varying(32) NOT NULL,
    synced_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_doctor_schedules_range CHECK ((end_time > start_time))
);


ALTER TABLE public.doctor_schedules OWNER TO healthcare;

--
-- Name: doctor_schedules_id_seq; Type: SEQUENCE; Schema: public; Owner: healthcare
--

CREATE SEQUENCE public.doctor_schedules_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.doctor_schedules_id_seq OWNER TO healthcare;

--
-- Name: doctor_schedules_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: healthcare
--

ALTER SEQUENCE public.doctor_schedules_id_seq OWNED BY public.doctor_schedules.id;


--
-- Name: doctors; Type: TABLE; Schema: public; Owner: healthcare
--

CREATE TABLE public.doctors (
    id integer NOT NULL,
    hospital_id integer NOT NULL,
    department_id integer NOT NULL,
    full_name character varying(150) NOT NULL,
    title character varying(100),
    qualifications text,
    experience_years integer NOT NULL,
    introduction text,
    consultation_fee numeric(12,2),
    avatar_url character varying(500),
    erp_doctor_id character varying(64),
    rating_avg numeric(3,2) NOT NULL,
    rating_count integer NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.doctors OWNER TO healthcare;

--
-- Name: doctors_id_seq; Type: SEQUENCE; Schema: public; Owner: healthcare
--

CREATE SEQUENCE public.doctors_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.doctors_id_seq OWNER TO healthcare;

--
-- Name: doctors_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: healthcare
--

ALTER SEQUENCE public.doctors_id_seq OWNED BY public.doctors.id;


--
-- Name: hospitals; Type: TABLE; Schema: public; Owner: healthcare
--

CREATE TABLE public.hospitals (
    id integer NOT NULL,
    name character varying(200) NOT NULL,
    facility_type character varying(32) NOT NULL,
    address character varying(255) NOT NULL,
    city character varying(100) NOT NULL,
    phone character varying(30),
    email character varying(255),
    website character varying(255),
    description text,
    is_active boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.hospitals OWNER TO healthcare;

--
-- Name: hospitals_id_seq; Type: SEQUENCE; Schema: public; Owner: healthcare
--

CREATE SEQUENCE public.hospitals_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.hospitals_id_seq OWNER TO healthcare;

--
-- Name: hospitals_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: healthcare
--

ALTER SEQUENCE public.hospitals_id_seq OWNED BY public.hospitals.id;


--
-- Name: notifications; Type: TABLE; Schema: public; Owner: healthcare
--

CREATE TABLE public.notifications (
    id integer NOT NULL,
    user_id integer NOT NULL,
    type character varying(32) NOT NULL,
    title character varying(200) NOT NULL,
    content text NOT NULL,
    link character varying(255),
    created_at timestamp with time zone NOT NULL,
    read_at timestamp with time zone
);


ALTER TABLE public.notifications OWNER TO healthcare;

--
-- Name: notifications_id_seq; Type: SEQUENCE; Schema: public; Owner: healthcare
--

CREATE SEQUENCE public.notifications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.notifications_id_seq OWNER TO healthcare;

--
-- Name: notifications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: healthcare
--

ALTER SEQUENCE public.notifications_id_seq OWNED BY public.notifications.id;


--
-- Name: patient_profiles; Type: TABLE; Schema: public; Owner: healthcare
--

CREATE TABLE public.patient_profiles (
    id integer NOT NULL,
    user_id integer NOT NULL,
    full_name character varying(100) NOT NULL,
    date_of_birth date NOT NULL,
    phone_number character varying(20) NOT NULL,
    address character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.patient_profiles OWNER TO healthcare;

--
-- Name: patient_profiles_id_seq; Type: SEQUENCE; Schema: public; Owner: healthcare
--

CREATE SEQUENCE public.patient_profiles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.patient_profiles_id_seq OWNER TO healthcare;

--
-- Name: patient_profiles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: healthcare
--

ALTER SEQUENCE public.patient_profiles_id_seq OWNED BY public.patient_profiles.id;


--
-- Name: payments; Type: TABLE; Schema: public; Owner: healthcare
--

CREATE TABLE public.payments (
    id integer NOT NULL,
    appointment_id integer NOT NULL,
    amount numeric(12,2) NOT NULL,
    currency character varying(3) NOT NULL,
    status character varying(32) NOT NULL,
    provider character varying(32) NOT NULL,
    provider_reference character varying(64),
    checkout_url character varying(500),
    failure_reason character varying(500),
    last_event_id character varying(64),
    paid_at timestamp with time zone,
    refunded_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.payments OWNER TO healthcare;

--
-- Name: payments_id_seq; Type: SEQUENCE; Schema: public; Owner: healthcare
--

CREATE SEQUENCE public.payments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.payments_id_seq OWNER TO healthcare;

--
-- Name: payments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: healthcare
--

ALTER SEQUENCE public.payments_id_seq OWNED BY public.payments.id;


--
-- Name: recommendation_logs; Type: TABLE; Schema: public; Owner: healthcare
--

CREATE TABLE public.recommendation_logs (
    id bigint NOT NULL,
    specialty_id integer NOT NULL,
    created_at timestamp with time zone NOT NULL
);


ALTER TABLE public.recommendation_logs OWNER TO healthcare;

--
-- Name: recommendation_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: healthcare
--

CREATE SEQUENCE public.recommendation_logs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.recommendation_logs_id_seq OWNER TO healthcare;

--
-- Name: recommendation_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: healthcare
--

ALTER SEQUENCE public.recommendation_logs_id_seq OWNED BY public.recommendation_logs.id;


--
-- Name: reviews; Type: TABLE; Schema: public; Owner: healthcare
--

CREATE TABLE public.reviews (
    id integer NOT NULL,
    appointment_id integer NOT NULL,
    patient_id integer NOT NULL,
    doctor_id integer NOT NULL,
    rating smallint NOT NULL,
    comment text,
    status character varying(32) NOT NULL,
    moderated_by integer,
    moderation_note character varying(500),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_reviews_rating_range CHECK (((rating >= 1) AND (rating <= 5)))
);


ALTER TABLE public.reviews OWNER TO healthcare;

--
-- Name: reviews_id_seq; Type: SEQUENCE; Schema: public; Owner: healthcare
--

CREATE SEQUENCE public.reviews_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.reviews_id_seq OWNER TO healthcare;

--
-- Name: reviews_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: healthcare
--

ALTER SEQUENCE public.reviews_id_seq OWNED BY public.reviews.id;


--
-- Name: specialties; Type: TABLE; Schema: public; Owner: healthcare
--

CREATE TABLE public.specialties (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    description text,
    is_active boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.specialties OWNER TO healthcare;

--
-- Name: specialties_id_seq; Type: SEQUENCE; Schema: public; Owner: healthcare
--

CREATE SEQUENCE public.specialties_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.specialties_id_seq OWNER TO healthcare;

--
-- Name: specialties_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: healthcare
--

ALTER SEQUENCE public.specialties_id_seq OWNED BY public.specialties.id;


--
-- Name: symptom_specialty_rules; Type: TABLE; Schema: public; Owner: healthcare
--

CREATE TABLE public.symptom_specialty_rules (
    id integer NOT NULL,
    symptom_id integer NOT NULL,
    specialty_id integer NOT NULL,
    weight double precision NOT NULL
);


ALTER TABLE public.symptom_specialty_rules OWNER TO healthcare;

--
-- Name: symptom_specialty_rules_id_seq; Type: SEQUENCE; Schema: public; Owner: healthcare
--

CREATE SEQUENCE public.symptom_specialty_rules_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.symptom_specialty_rules_id_seq OWNER TO healthcare;

--
-- Name: symptom_specialty_rules_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: healthcare
--

ALTER SEQUENCE public.symptom_specialty_rules_id_seq OWNED BY public.symptom_specialty_rules.id;


--
-- Name: symptoms; Type: TABLE; Schema: public; Owner: healthcare
--

CREATE TABLE public.symptoms (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    description text,
    keywords character varying(500),
    is_red_flag boolean NOT NULL,
    red_flag_message character varying(500),
    is_active boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.symptoms OWNER TO healthcare;

--
-- Name: symptoms_id_seq; Type: SEQUENCE; Schema: public; Owner: healthcare
--

CREATE SEQUENCE public.symptoms_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.symptoms_id_seq OWNER TO healthcare;

--
-- Name: symptoms_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: healthcare
--

ALTER SEQUENCE public.symptoms_id_seq OWNED BY public.symptoms.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: healthcare
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email character varying(255) NOT NULL,
    password_hash character varying(255) NOT NULL,
    role character varying(32) NOT NULL,
    account_status character varying(32) NOT NULL,
    last_login_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.users OWNER TO healthcare;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: healthcare
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO healthcare;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: healthcare
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: appointment_status_history id; Type: DEFAULT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.appointment_status_history ALTER COLUMN id SET DEFAULT nextval('public.appointment_status_history_id_seq'::regclass);


--
-- Name: appointment_types id; Type: DEFAULT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.appointment_types ALTER COLUMN id SET DEFAULT nextval('public.appointment_types_id_seq'::regclass);


--
-- Name: appointments id; Type: DEFAULT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.appointments ALTER COLUMN id SET DEFAULT nextval('public.appointments_id_seq'::regclass);


--
-- Name: audit_logs id; Type: DEFAULT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.audit_logs ALTER COLUMN id SET DEFAULT nextval('public.audit_logs_id_seq'::regclass);


--
-- Name: departments id; Type: DEFAULT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.departments ALTER COLUMN id SET DEFAULT nextval('public.departments_id_seq'::regclass);


--
-- Name: doctor_schedules id; Type: DEFAULT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.doctor_schedules ALTER COLUMN id SET DEFAULT nextval('public.doctor_schedules_id_seq'::regclass);


--
-- Name: doctors id; Type: DEFAULT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.doctors ALTER COLUMN id SET DEFAULT nextval('public.doctors_id_seq'::regclass);


--
-- Name: hospitals id; Type: DEFAULT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.hospitals ALTER COLUMN id SET DEFAULT nextval('public.hospitals_id_seq'::regclass);


--
-- Name: notifications id; Type: DEFAULT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.notifications ALTER COLUMN id SET DEFAULT nextval('public.notifications_id_seq'::regclass);


--
-- Name: patient_profiles id; Type: DEFAULT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.patient_profiles ALTER COLUMN id SET DEFAULT nextval('public.patient_profiles_id_seq'::regclass);


--
-- Name: payments id; Type: DEFAULT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.payments ALTER COLUMN id SET DEFAULT nextval('public.payments_id_seq'::regclass);


--
-- Name: recommendation_logs id; Type: DEFAULT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.recommendation_logs ALTER COLUMN id SET DEFAULT nextval('public.recommendation_logs_id_seq'::regclass);


--
-- Name: reviews id; Type: DEFAULT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.reviews ALTER COLUMN id SET DEFAULT nextval('public.reviews_id_seq'::regclass);


--
-- Name: specialties id; Type: DEFAULT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.specialties ALTER COLUMN id SET DEFAULT nextval('public.specialties_id_seq'::regclass);


--
-- Name: symptom_specialty_rules id; Type: DEFAULT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.symptom_specialty_rules ALTER COLUMN id SET DEFAULT nextval('public.symptom_specialty_rules_id_seq'::regclass);


--
-- Name: symptoms id; Type: DEFAULT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.symptoms ALTER COLUMN id SET DEFAULT nextval('public.symptoms_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: healthcare
--

COPY public.alembic_version (version_num) FROM stdin;
0001_initial
\.


--
-- Data for Name: appointment_status_history; Type: TABLE DATA; Schema: public; Owner: healthcare
--

COPY public.appointment_status_history (id, appointment_id, field, from_value, to_value, reason, source, created_at) FROM stdin;
1	1	status	\N	PENDING	\N	PATIENT	2026-10-31 11:28:58.041517+00
2	1	status	PENDING	CONFIRMED	\N	ERP	2026-10-31 11:28:58.041519+00
3	1	check_in_status	NOT_CHECKED_IN	CHECKED_IN	\N	ERP	2026-10-31 11:28:58.041519+00
4	1	status	CONFIRMED	COMPLETED	\N	ERP	2026-10-31 11:28:58.04152+00
5	2	status	\N	PENDING	Booking request submitted	PATIENT	2026-10-31 11:35:01.512613+00
6	2	status	PENDING	CONFIRMED	\N	ERP	2026-10-31 11:35:01.60277+00
7	2	status	CONFIRMED	CANCELLED	Plans changed	PATIENT	2026-10-31 11:35:03.350133+00
8	3	status	\N	PENDING	Booking request submitted	PATIENT	2026-10-31 11:40:47.850215+00
9	3	status	PENDING	CONFIRMED	\N	ERP	2026-10-31 11:40:47.927998+00
10	3	status	CONFIRMED	CANCELLED	Plans changed	PATIENT	2026-10-31 11:40:49.70305+00
11	4	status	\N	PENDING	Booking request submitted	PATIENT	2026-10-31 11:42:09.696595+00
12	4	status	PENDING	CONFIRMED	\N	ERP	2026-10-31 11:42:09.761501+00
13	4	status	CONFIRMED	CANCELLED	Plans changed	PATIENT	2026-10-31 11:42:11.491768+00
14	5	status	\N	PENDING	Booking request submitted	PATIENT	2026-10-31 12:02:20.3586+00
15	5	status	PENDING	CONFIRMED	\N	ERP	2026-10-31 12:02:20.420572+00
16	5	status	CONFIRMED	CANCELLED	Plans changed	PATIENT	2026-10-31 12:02:22.108864+00
17	6	status	\N	PENDING	Booking request submitted	PATIENT	2026-11-07 01:48:29.347404+00
18	6	status	PENDING	CONFIRMED	\N	ERP	2026-11-07 01:48:29.415667+00
19	6	check_in_status	NOT_CHECKED_IN	CHECKED_IN	\N	ERP	2026-11-07 01:48:29.651103+00
20	6	status	CONFIRMED	COMPLETED	\N	ERP	2026-11-07 01:48:29.687234+00
21	7	status	\N	PENDING	Booking request submitted	PATIENT	2026-11-07 01:48:29.761035+00
22	7	status	PENDING	CONFIRMED	\N	ERP	2026-11-07 01:48:29.817139+00
23	7	status	CONFIRMED	CANCELLED	Smoke test	PATIENT	2026-11-07 01:48:29.892414+00
24	8	status	\N	PENDING	Booking request submitted	PATIENT	2026-11-07 01:48:29.94824+00
25	8	status	PENDING	CONFIRMED	\N	ERP	2026-11-07 01:48:30.004748+00
\.


--
-- Data for Name: appointment_types; Type: TABLE DATA; Schema: public; Owner: healthcare
--

COPY public.appointment_types (id, name, description, duration_minutes, buffer_minutes, fee_override, specialty_id, doctor_id, is_active, created_at, updated_at) FROM stdin;
1	Standard consultation	General consultation.	20	10	\N	\N	\N	t	2026-10-31 11:28:57.863826+00	2026-10-31 11:28:57.863827+00
2	Extended consultation	For complex or multiple concerns.	30	10	\N	\N	\N	t	2026-10-31 11:28:57.863827+00	2026-10-31 11:28:57.863828+00
3	Follow-up visit	Review of a previous consultation or test results.	15	5	150000.00	\N	\N	t	2026-10-31 11:28:57.863828+00	2026-10-31 11:28:57.863828+00
4	Skin procedure consultation	Assessment before a minor skin procedure.	40	10	\N	5	\N	t	2026-10-31 11:28:57.863829+00	2026-10-31 11:28:57.863829+00
5	Comprehensive eye examination	Vision and eye health check.	30	10	\N	6	\N	t	2026-10-31 11:28:57.86383+00	2026-10-31 11:28:57.86383+00
6	Smoke type	\N	25	5	\N	1	\N	t	2026-11-07 01:48:30.319497+00	2026-11-07 01:48:30.319499+00
\.


--
-- Data for Name: appointments; Type: TABLE DATA; Schema: public; Owner: healthcare
--

COPY public.appointments (id, booking_reference, patient_id, doctor_id, appointment_type_id, start_time, end_time, end_with_buffer, status, status_reason, check_in_status, erp_booking_id, reason_for_visit, fee_amount, currency, cancelled_at, created_at, updated_at) FROM stdin;
1	HKUMEVWHGY	1	1	1	2026-10-24 02:00:00+00	2026-10-24 02:20:00+00	2026-10-24 02:30:00+00	COMPLETED	\N	CHECKED_IN	ERP-DEMO-0001	Demo appointment	250000.00	VND	\N	2026-10-31 11:28:58.03933+00	2026-10-31 11:28:58.039331+00
2	HKHE8BY2E3	2	23	3	2026-11-02 06:30:00+00	2026-11-02 06:45:00+00	2026-11-02 06:50:00+00	CANCELLED	Plans changed	NOT_CHECKED_IN	ERP-0787F945C2	Annual check-up	150000.00	VND	2026-10-31 11:35:03.346801+00	2026-10-31 11:35:01.50942+00	2026-10-31 11:35:03.349005+00
3	HKA9HX3RHX	3	23	3	2026-11-02 06:30:00+00	2026-11-02 06:45:00+00	2026-11-02 06:50:00+00	CANCELLED	Plans changed	NOT_CHECKED_IN	ERP-85C9056946	Annual check-up	150000.00	VND	2026-10-31 11:40:49.700788+00	2026-10-31 11:40:47.848991+00	2026-10-31 11:40:49.702374+00
4	HKLLYS9XU7	4	23	3	2026-11-02 06:30:00+00	2026-11-02 06:45:00+00	2026-11-02 06:50:00+00	CANCELLED	Plans changed	NOT_CHECKED_IN	ERP-906B6181FC	Annual check-up	150000.00	VND	2026-10-31 11:42:11.488945+00	2026-10-31 11:42:09.694386+00	2026-10-31 11:42:11.49058+00
5	HKCGJVQ3CG	5	23	3	2026-11-02 06:30:00+00	2026-11-02 06:45:00+00	2026-11-02 06:50:00+00	CANCELLED	Plans changed	NOT_CHECKED_IN	ERP-C075115E72	Annual check-up	150000.00	VND	2026-10-31 12:02:22.106794+00	2026-10-31 12:02:20.356569+00	2026-10-31 12:02:22.108276+00
6	HKBF3GEYSJ	1	23	3	2026-11-09 06:30:00+00	2026-11-09 06:45:00+00	2026-11-09 06:50:00+00	COMPLETED	\N	CHECKED_IN	ERP-ABD885282C	Smoke test	150000.00	VND	\N	2026-11-07 01:48:29.343598+00	2026-11-07 01:48:29.686521+00
7	HK46HZ3CDG	1	15	3	2026-11-10 06:30:00+00	2026-11-10 06:45:00+00	2026-11-10 06:50:00+00	CANCELLED	Smoke test	NOT_CHECKED_IN	ERP-3CA2EAD2F6	\N	150000.00	VND	2026-11-07 01:48:29.890186+00	2026-11-07 01:48:29.760203+00	2026-11-07 01:48:29.891747+00
8	HKLJN84UF7	1	7	3	2026-11-11 06:30:00+00	2026-11-11 06:45:00+00	2026-11-11 06:50:00+00	CONFIRMED	\N	NOT_CHECKED_IN	ERP-482051A901	\N	150000.00	VND	\N	2026-11-07 01:48:29.947567+00	2026-11-07 01:48:30.003876+00
\.


--
-- Data for Name: audit_logs; Type: TABLE DATA; Schema: public; Owner: healthcare
--

COPY public.audit_logs (id, actor_id, actor_type, action, entity_type, entity_id, details, request_id, created_at) FROM stdin;
1	3	USER	user.registered	user	3	null	a1d4e13ac95b9840f95524dc0f071a15	2026-10-31 11:34:59.91403+00
2	3	USER	appointment.created	appointment	2	{"doctor_id": 23, "booking_reference": "HKHE8BY2E3"}	03850e282bc5a6749e9565d943bbf662	2026-10-31 11:35:01.514609+00
3	\N	ERP	appointment.status_changed	appointment	2	{"to": "CONFIRMED", "from": "PENDING", "source": "ERP"}	03850e282bc5a6749e9565d943bbf662	2026-10-31 11:35:01.601827+00
4	3	USER	payment.initiated	payment	1	{"amount": "150000.00", "appointment_id": 2}	c1c786032a5dbe2369eae79948242372	2026-10-31 11:35:02.071972+00
5	\N	PAYMENT_GATEWAY	payment.status_changed	payment	1	{"to": "PAID", "from": "PENDING", "provider_event_id": "e0841edef62948db99f3f2c53cb5af5c"}	48c02f629c91446b83d0938ddd3cfc90	2026-10-31 11:35:02.237189+00
6	3	USER	appointment.status_changed	appointment	2	{"to": "CANCELLED", "from": "CONFIRMED", "source": "PATIENT"}	e25cb7c3c9aeda93c544c10c828700de	2026-10-31 11:35:03.347674+00
7	\N	PAYMENT_GATEWAY	payment.refunded	payment	1	{"refund_reference": "RF-E4FEFA2611A6"}	e25cb7c3c9aeda93c544c10c828700de	2026-10-31 11:35:03.356374+00
8	1	USER	specialty.created	specialty	12	null	a17c0d5379cc8ba2480469393de02271	2026-10-31 11:35:06.258015+00
9	4	USER	user.registered	user	4	null	ede498fa1ccefd1057c9e33e14078aad	2026-10-31 11:40:46.393347+00
10	4	USER	appointment.created	appointment	3	{"doctor_id": 23, "booking_reference": "HKA9HX3RHX"}	c25a2a3e30eb1f0d7632fbc619391ba1	2026-10-31 11:40:47.850996+00
11	\N	ERP	appointment.status_changed	appointment	3	{"to": "CONFIRMED", "from": "PENDING", "source": "ERP"}	c25a2a3e30eb1f0d7632fbc619391ba1	2026-10-31 11:40:47.927127+00
12	4	USER	payment.initiated	payment	2	{"amount": "150000.00", "appointment_id": 3}	d1399163f95177c509e9c16a73df8d0b	2026-10-31 11:40:48.337811+00
13	\N	PAYMENT_GATEWAY	payment.status_changed	payment	2	{"to": "PAID", "from": "PENDING", "provider_event_id": "a1c4c59535904eb884bc17bc25eba278"}	70e9d3c66249445d9731f4b67ca67dde	2026-10-31 11:40:48.567321+00
14	4	USER	appointment.status_changed	appointment	3	{"to": "CANCELLED", "from": "CONFIRMED", "source": "PATIENT"}	a18f2686ceb7d4e933bb9d94f7e7c1b5	2026-10-31 11:40:49.701611+00
15	\N	PAYMENT_GATEWAY	payment.refunded	payment	2	{"refund_reference": "RF-B297C9B9824D"}	a18f2686ceb7d4e933bb9d94f7e7c1b5	2026-10-31 11:40:49.70859+00
16	1	USER	specialty.created	specialty	13	null	d1b921420b16a664068dc38be5e4aeeb	2026-10-31 11:40:52.661946+00
17	5	USER	user.registered	user	5	null	4144f49a85587de431d08300aa3da70e	2026-10-31 11:42:08.221542+00
18	5	USER	appointment.created	appointment	4	{"doctor_id": 23, "booking_reference": "HKLLYS9XU7"}	79e313b1f15cca8097336b5535387ed3	2026-10-31 11:42:09.697097+00
19	\N	ERP	appointment.status_changed	appointment	4	{"to": "CONFIRMED", "from": "PENDING", "source": "ERP"}	79e313b1f15cca8097336b5535387ed3	2026-10-31 11:42:09.761065+00
20	5	USER	payment.initiated	payment	3	{"amount": "150000.00", "appointment_id": 4}	d2635395f1a016bcd1a41d264f2844a7	2026-10-31 11:42:10.181186+00
21	\N	PAYMENT_GATEWAY	payment.status_changed	payment	3	{"to": "PAID", "from": "PENDING", "provider_event_id": "974576b3088449608c6df226b61b1e2a"}	5a88d631fa2c4038a3ae1e11ee90051e	2026-10-31 11:42:10.351845+00
22	5	USER	appointment.status_changed	appointment	4	{"to": "CANCELLED", "from": "CONFIRMED", "source": "PATIENT"}	a031dd16969ce9d3d27c5737bb11b0f6	2026-10-31 11:42:11.489838+00
23	\N	PAYMENT_GATEWAY	payment.refunded	payment	3	{"refund_reference": "RF-1E9E1DFAB721"}	a031dd16969ce9d3d27c5737bb11b0f6	2026-10-31 11:42:11.498863+00
24	1	USER	specialty.created	specialty	14	null	54168e4d7cf20e36adccf91f669d841b	2026-10-31 11:42:14.427505+00
25	6	USER	user.registered	user	6	null	bcb658a642286dd3ae65b2ad9e12e896	2026-10-31 12:02:18.898132+00
26	6	USER	appointment.created	appointment	5	{"doctor_id": 23, "booking_reference": "HKCGJVQ3CG"}	266b40669fb7def06b4051d82acbd5e6	2026-10-31 12:02:20.359528+00
27	\N	ERP	appointment.status_changed	appointment	5	{"to": "CONFIRMED", "from": "PENDING", "source": "ERP"}	266b40669fb7def06b4051d82acbd5e6	2026-10-31 12:02:20.420115+00
28	6	USER	payment.initiated	payment	4	{"amount": "150000.00", "appointment_id": 5}	4ade84d8b5d51b2b57a7f6378582627d	2026-10-31 12:02:20.840597+00
29	\N	PAYMENT_GATEWAY	payment.status_changed	payment	4	{"to": "PAID", "from": "PENDING", "provider_event_id": "0892e32ae07d4bf985dd77accbd9d117"}	e689a1356cff41f9bebea452d0b2afa2	2026-10-31 12:02:21.022568+00
30	6	USER	appointment.status_changed	appointment	5	{"to": "CANCELLED", "from": "CONFIRMED", "source": "PATIENT"}	02e73aee97c20608a24cdc92caee8ffa	2026-10-31 12:02:22.107626+00
31	\N	PAYMENT_GATEWAY	payment.refunded	payment	4	{"refund_reference": "RF-6BE644D09362"}	02e73aee97c20608a24cdc92caee8ffa	2026-10-31 12:02:22.114189+00
32	1	USER	specialty.created	specialty	15	null	908c0abb27b78a3bf75f52f0fa1e3df5	2026-10-31 12:02:24.983592+00
33	7	USER	user.registered	user	7	null	94fd9fbd5a88b72bc9f614be2a17ed82	2026-11-07 01:48:29.20887+00
34	7	USER	profile.updated	patient_profile	6	{"fields": ["address"]}	78078471789406cfa54e070160cba34d	2026-11-07 01:48:29.234872+00
35	2	USER	appointment.created	appointment	6	{"doctor_id": 23, "booking_reference": "HKBF3GEYSJ"}	be8e8c2497fa371cbaa87fb2929bd6fe	2026-11-07 01:48:29.349425+00
36	\N	ERP	appointment.status_changed	appointment	6	{"to": "CONFIRMED", "from": "PENDING", "source": "ERP"}	be8e8c2497fa371cbaa87fb2929bd6fe	2026-11-07 01:48:29.41536+00
37	2	USER	payment.initiated	payment	5	{"amount": "150000.00", "appointment_id": 6}	3850b5b5bea38e273263aeafc2a77397	2026-11-07 01:48:29.509845+00
38	\N	PAYMENT_GATEWAY	payment.status_changed	payment	5	{"to": "PAID", "from": "PENDING", "provider_event_id": "c16ce70b1d9e4e1c90b6c486353f6f42"}	5ef1e2d7565e4f1ca2fc7b0143e5598e	2026-11-07 01:48:29.565817+00
39	\N	ERP	appointment.check_in_changed	appointment	6	{"to": "CHECKED_IN", "from": "NOT_CHECKED_IN"}	be26a2ae67db47c296437f35764e28de	2026-11-07 01:48:29.649867+00
40	\N	ERP	appointment.status_changed	appointment	6	{"to": "COMPLETED", "from": "CONFIRMED", "source": "ERP"}	1f0211c40a23480999a25438d6b78065	2026-11-07 01:48:29.685564+00
41	2	USER	review.created	review	1	{"rating": 5, "doctor_id": 23}	a6b76fba8f804c90c49c7b4709403f86	2026-11-07 01:48:29.713445+00
42	2	USER	appointment.created	appointment	7	{"doctor_id": 15, "booking_reference": "HK46HZ3CDG"}	6f470aae21cea0447aebd8ee05717eb0	2026-11-07 01:48:29.761673+00
43	\N	ERP	appointment.status_changed	appointment	7	{"to": "CONFIRMED", "from": "PENDING", "source": "ERP"}	6f470aae21cea0447aebd8ee05717eb0	2026-11-07 01:48:29.816851+00
44	2	USER	payment.initiated	payment	6	{"amount": "150000.00", "appointment_id": 7}	939056249aef87b321d74983920a0c31	2026-11-07 01:48:29.834989+00
45	\N	PAYMENT_GATEWAY	payment.status_changed	payment	6	{"to": "PAID", "from": "PENDING", "provider_event_id": "98dea078a71d4843a085aec7611b10ad"}	b559e345657743e593336410a10e1279	2026-11-07 01:48:29.867832+00
46	2	USER	appointment.status_changed	appointment	7	{"to": "CANCELLED", "from": "CONFIRMED", "source": "PATIENT"}	06e5bc9d0786df9a8816f26c095b93db	2026-11-07 01:48:29.890876+00
49	\N	ERP	appointment.status_changed	appointment	8	{"to": "CONFIRMED", "from": "PENDING", "source": "ERP"}	f2b16c3255a02ef48666c5a289245dbf	2026-11-07 01:48:30.004463+00
50	2	USER	payment.initiated	payment	7	{"amount": "150000.00", "appointment_id": 8}	84596d65c12eaf40bfdc671b91583dc4	2026-11-07 01:48:30.019888+00
53	1	USER	review.moderated	review	1	{"to": "HIDDEN", "from": "PUBLISHED"}	7c597cd4a470dacaa0868e261ce6c13b	2026-11-07 01:48:30.222666+00
54	1	USER	review.moderated	review	1	{"to": "PUBLISHED", "from": "HIDDEN"}	4306427ab57003f5c511267ad6f9e396	2026-11-07 01:48:30.236152+00
58	1	USER	erp.schedule_sync	doctor_schedule	\N	{"failed": 0, "synced": 28}	f8c04330453c6c59b89c22a04ab22df9	2026-11-07 01:48:30.530659+00
59	1	USER	user.status_changed	user	7	{"to": "INACTIVE", "from": "ACTIVE"}	fac5e8c6ade40d7bcd9ec9412c46384f	2026-11-07 01:48:30.548414+00
61	2	USER	user.password_reset	user	2	null	8efda600fa67639f8ab8fd3f05bb6775	2026-11-07 01:48:30.705608+00
47	\N	PAYMENT_GATEWAY	payment.refunded	payment	6	{"refund_reference": "RF-3971FF6B322C"}	06e5bc9d0786df9a8816f26c095b93db	2026-11-07 01:48:29.896652+00
48	2	USER	appointment.created	appointment	8	{"doctor_id": 7, "booking_reference": "HKLJN84UF7"}	f2b16c3255a02ef48666c5a289245dbf	2026-11-07 01:48:29.948839+00
51	\N	PAYMENT_GATEWAY	payment.status_changed	payment	7	{"to": "FAILED", "from": "PENDING", "provider_event_id": "68637bfe52e045239b227af1215ababc"}	701c3a69be104b5385d4e53e361f6143	2026-11-07 01:48:30.04839+00
52	2	USER	payment.initiated	payment	8	{"amount": "150000.00", "appointment_id": 8}	7bd9e5451e329fab79f90ece20ad0611	2026-11-07 01:48:30.067986+00
55	1	USER	hospital.created	hospital	4	null	23fa593fcc8a1911d1b35c96959e20df	2026-11-07 01:48:30.247817+00
56	1	USER	hospital.updated	hospital	4	{"fields": ["is_active"]}	89b098e1ea95df2ebece29057f08dae9	2026-11-07 01:48:30.259617+00
57	1	USER	appointment_type.created	appointment_type	6	null	39fedaaefca84f653051c2d83210e84f	2026-11-07 01:48:30.322087+00
60	2	USER	user.password_reset_requested	user	2	null	1d05deb3b43610f56759ceebce20c028	2026-11-07 01:48:30.643074+00
62	8	USER	user.registered	user	8	null	5254157c13ec6da90989f43984fb69fa	2026-11-07 01:49:48.098237+00
63	8	USER	profile.updated	patient_profile	7	{"fields": ["address"]}	e6ba5f7434aeb35de85769f1988ff293	2026-11-07 01:49:58.416569+00
\.


--
-- Data for Name: departments; Type: TABLE DATA; Schema: public; Owner: healthcare
--

COPY public.departments (id, hospital_id, specialty_id, name, description, is_active, created_at, updated_at) FROM stdin;
1	1	1	General Internal Medicine Department	\N	t	2026-10-31 11:28:57.835232+00	2026-10-31 11:28:57.835233+00
2	1	2	Respiratory Medicine Department	\N	t	2026-10-31 11:28:57.837707+00	2026-10-31 11:28:57.837709+00
3	1	3	Cardiology Department	\N	t	2026-10-31 11:28:57.842056+00	2026-10-31 11:28:57.842059+00
4	1	4	Gastroenterology Department	\N	t	2026-10-31 11:28:57.845702+00	2026-10-31 11:28:57.845705+00
5	1	10	Neurology Department	\N	t	2026-10-31 11:28:57.84792+00	2026-10-31 11:28:57.847922+00
6	1	7	Orthopedics Department	\N	t	2026-10-31 11:28:57.849549+00	2026-10-31 11:28:57.849551+00
7	2	5	Dermatology Department	\N	t	2026-10-31 11:28:57.852337+00	2026-10-31 11:28:57.852339+00
8	2	6	Ophthalmology Department	\N	t	2026-10-31 11:28:57.85303+00	2026-10-31 11:28:57.853031+00
9	3	1	General Internal Medicine Department	\N	t	2026-10-31 11:28:57.855545+00	2026-10-31 11:28:57.855546+00
10	3	11	Pediatrics Department	\N	t	2026-10-31 11:28:57.856319+00	2026-10-31 11:28:57.856321+00
11	3	9	Otorhinolaryngology (ENT) Department	\N	t	2026-10-31 11:28:57.857415+00	2026-10-31 11:28:57.857417+00
12	3	8	Rheumatology Department	\N	t	2026-10-31 11:28:57.858382+00	2026-10-31 11:28:57.858383+00
13	3	7	Orthopedics Department	\N	t	2026-10-31 11:28:57.860101+00	2026-10-31 11:28:57.860102+00
14	3	2	Respiratory Medicine Department	\N	t	2026-10-31 11:28:57.861778+00	2026-10-31 11:28:57.86178+00
\.


--
-- Data for Name: doctor_schedules; Type: TABLE DATA; Schema: public; Owner: healthcare
--

COPY public.doctor_schedules (id, doctor_id, start_time, end_time, max_appointments, is_available, source, synced_at) FROM stdin;
2745	1	2026-11-02 01:00:00+00	2026-11-02 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.463487+00
2746	1	2026-11-02 06:30:00+00	2026-11-02 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.463487+00
2747	1	2026-11-03 01:00:00+00	2026-11-03 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.463487+00
2748	1	2026-11-03 06:30:00+00	2026-11-03 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.463487+00
2749	1	2026-11-04 01:00:00+00	2026-11-04 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.463487+00
2750	1	2026-11-04 06:30:00+00	2026-11-04 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.463487+00
2751	1	2026-11-05 01:00:00+00	2026-11-05 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.463487+00
2752	1	2026-11-05 06:30:00+00	2026-11-05 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.463487+00
2753	1	2026-11-06 01:00:00+00	2026-11-06 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.463487+00
2754	1	2026-11-06 06:30:00+00	2026-11-06 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.463487+00
5496	3	2026-11-07 01:00:00+00	2026-11-07 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.70612+00
5497	3	2026-11-09 01:00:00+00	2026-11-09 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.70612+00
5498	3	2026-11-09 06:30:00+00	2026-11-09 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.70612+00
5499	3	2026-11-10 01:00:00+00	2026-11-10 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.70612+00
5500	3	2026-11-10 06:30:00+00	2026-11-10 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.70612+00
5501	3	2026-11-11 01:00:00+00	2026-11-11 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.70612+00
5502	3	2026-11-11 06:30:00+00	2026-11-11 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.70612+00
5503	3	2026-11-12 01:00:00+00	2026-11-12 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.70612+00
5504	3	2026-11-12 06:30:00+00	2026-11-12 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.70612+00
5505	3	2026-11-13 01:00:00+00	2026-11-13 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.70612+00
5506	3	2026-11-13 06:30:00+00	2026-11-13 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.70612+00
5507	3	2026-11-14 01:00:00+00	2026-11-14 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.70612+00
2791	3	2026-11-02 01:00:00+00	2026-11-02 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.47987+00
2792	3	2026-11-02 06:30:00+00	2026-11-02 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.47987+00
2793	3	2026-11-03 01:00:00+00	2026-11-03 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.47987+00
2794	3	2026-11-03 06:30:00+00	2026-11-03 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.47987+00
2795	3	2026-11-04 01:00:00+00	2026-11-04 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.47987+00
2796	3	2026-11-04 06:30:00+00	2026-11-04 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.47987+00
2797	3	2026-11-05 01:00:00+00	2026-11-05 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.47987+00
2798	3	2026-11-05 06:30:00+00	2026-11-05 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.47987+00
2799	3	2026-11-06 01:00:00+00	2026-11-06 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.47987+00
2800	3	2026-11-06 06:30:00+00	2026-11-06 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.47987+00
5508	3	2026-11-16 01:00:00+00	2026-11-16 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.70612+00
5509	3	2026-11-16 06:30:00+00	2026-11-16 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.70612+00
5510	3	2026-11-17 01:00:00+00	2026-11-17 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.70612+00
5511	3	2026-11-17 06:30:00+00	2026-11-17 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.70612+00
5512	3	2026-11-18 01:00:00+00	2026-11-18 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.70612+00
5513	3	2026-11-18 06:30:00+00	2026-11-18 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.70612+00
5514	3	2026-11-19 01:00:00+00	2026-11-19 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.70612+00
5515	3	2026-11-19 06:30:00+00	2026-11-19 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.70612+00
5516	3	2026-11-20 01:00:00+00	2026-11-20 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.70612+00
5517	3	2026-11-20 06:30:00+00	2026-11-20 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.70612+00
5518	3	2026-11-21 01:00:00+00	2026-11-21 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.70612+00
5594	7	2026-11-07 01:00:00+00	2026-11-07 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.731484+00
2837	5	2026-11-02 01:00:00+00	2026-11-02 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.489265+00
2838	5	2026-11-02 06:30:00+00	2026-11-02 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.489265+00
2839	5	2026-11-03 01:00:00+00	2026-11-03 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.489265+00
2840	5	2026-11-03 06:30:00+00	2026-11-03 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.489265+00
2841	5	2026-11-04 01:00:00+00	2026-11-04 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.489265+00
2842	5	2026-11-04 06:30:00+00	2026-11-04 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.489265+00
2843	5	2026-11-05 01:00:00+00	2026-11-05 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.489265+00
2844	5	2026-11-05 06:30:00+00	2026-11-05 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.489265+00
2845	5	2026-11-06 01:00:00+00	2026-11-06 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.489265+00
2846	5	2026-11-06 06:30:00+00	2026-11-06 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.489265+00
5595	7	2026-11-09 01:00:00+00	2026-11-09 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.731484+00
5596	7	2026-11-09 06:30:00+00	2026-11-09 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.731484+00
5597	7	2026-11-10 01:00:00+00	2026-11-10 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.731484+00
5598	7	2026-11-10 06:30:00+00	2026-11-10 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.731484+00
5599	7	2026-11-11 01:00:00+00	2026-11-11 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.731484+00
5600	7	2026-11-11 06:30:00+00	2026-11-11 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.731484+00
5601	7	2026-11-12 01:00:00+00	2026-11-12 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.731484+00
5602	7	2026-11-12 06:30:00+00	2026-11-12 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.731484+00
5603	7	2026-11-13 01:00:00+00	2026-11-13 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.731484+00
5604	7	2026-11-13 06:30:00+00	2026-11-13 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.731484+00
5605	7	2026-11-14 01:00:00+00	2026-11-14 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.731484+00
5606	7	2026-11-16 01:00:00+00	2026-11-16 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.731484+00
2883	7	2026-11-02 01:00:00+00	2026-11-02 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.498898+00
2884	7	2026-11-02 06:30:00+00	2026-11-02 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.498898+00
2885	7	2026-11-03 01:00:00+00	2026-11-03 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.498898+00
2886	7	2026-11-03 06:30:00+00	2026-11-03 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.498898+00
2887	7	2026-11-04 01:00:00+00	2026-11-04 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.498898+00
2888	7	2026-11-04 06:30:00+00	2026-11-04 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.498898+00
2889	7	2026-11-05 01:00:00+00	2026-11-05 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.498898+00
2890	7	2026-11-05 06:30:00+00	2026-11-05 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.498898+00
2891	7	2026-11-06 01:00:00+00	2026-11-06 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.498898+00
2892	7	2026-11-06 06:30:00+00	2026-11-06 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.498898+00
5607	7	2026-11-16 06:30:00+00	2026-11-16 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.731484+00
5608	7	2026-11-17 01:00:00+00	2026-11-17 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.731484+00
5609	7	2026-11-17 06:30:00+00	2026-11-17 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.731484+00
5610	7	2026-11-18 01:00:00+00	2026-11-18 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.731484+00
5611	7	2026-11-18 06:30:00+00	2026-11-18 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.731484+00
5612	7	2026-11-19 01:00:00+00	2026-11-19 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.731484+00
5613	7	2026-11-19 06:30:00+00	2026-11-19 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.731484+00
5614	7	2026-11-20 01:00:00+00	2026-11-20 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.731484+00
5615	7	2026-11-20 06:30:00+00	2026-11-20 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.731484+00
5616	7	2026-11-21 01:00:00+00	2026-11-21 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.731484+00
5692	11	2026-11-07 01:00:00+00	2026-11-07 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.754438+00
5693	11	2026-11-09 01:00:00+00	2026-11-09 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.754438+00
2929	9	2026-11-02 01:00:00+00	2026-11-02 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.508573+00
2930	9	2026-11-02 06:30:00+00	2026-11-02 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.508573+00
2931	9	2026-11-03 01:00:00+00	2026-11-03 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.508573+00
2932	9	2026-11-03 06:30:00+00	2026-11-03 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.508573+00
2933	9	2026-11-04 01:00:00+00	2026-11-04 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.508573+00
2934	9	2026-11-04 06:30:00+00	2026-11-04 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.508573+00
2935	9	2026-11-05 01:00:00+00	2026-11-05 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.508573+00
2936	9	2026-11-05 06:30:00+00	2026-11-05 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.508573+00
2937	9	2026-11-06 01:00:00+00	2026-11-06 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.508573+00
2938	9	2026-11-06 06:30:00+00	2026-11-06 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.508573+00
5694	11	2026-11-09 06:30:00+00	2026-11-09 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.754438+00
5695	11	2026-11-10 01:00:00+00	2026-11-10 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.754438+00
5696	11	2026-11-10 06:30:00+00	2026-11-10 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.754438+00
5697	11	2026-11-11 01:00:00+00	2026-11-11 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.754438+00
5698	11	2026-11-11 06:30:00+00	2026-11-11 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.754438+00
5699	11	2026-11-12 01:00:00+00	2026-11-12 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.754438+00
5700	11	2026-11-12 06:30:00+00	2026-11-12 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.754438+00
5701	11	2026-11-13 01:00:00+00	2026-11-13 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.754438+00
5702	11	2026-11-13 06:30:00+00	2026-11-13 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.754438+00
5703	11	2026-11-14 01:00:00+00	2026-11-14 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.754438+00
5704	11	2026-11-16 01:00:00+00	2026-11-16 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.754438+00
5705	11	2026-11-16 06:30:00+00	2026-11-16 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.754438+00
2975	11	2026-11-02 01:00:00+00	2026-11-02 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.518563+00
2976	11	2026-11-02 06:30:00+00	2026-11-02 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.518563+00
2977	11	2026-11-03 01:00:00+00	2026-11-03 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.518563+00
2978	11	2026-11-03 06:30:00+00	2026-11-03 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.518563+00
2979	11	2026-11-04 01:00:00+00	2026-11-04 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.518563+00
2980	11	2026-11-04 06:30:00+00	2026-11-04 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.518563+00
2981	11	2026-11-05 01:00:00+00	2026-11-05 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.518563+00
2982	11	2026-11-05 06:30:00+00	2026-11-05 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.518563+00
2983	11	2026-11-06 01:00:00+00	2026-11-06 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.518563+00
2984	11	2026-11-06 06:30:00+00	2026-11-06 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.518563+00
2767	2	2026-11-02 01:00:00+00	2026-11-02 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.474072+00
2768	2	2026-11-02 06:30:00+00	2026-11-02 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.474072+00
2769	2	2026-11-03 01:00:00+00	2026-11-03 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.474072+00
2770	2	2026-11-03 06:30:00+00	2026-11-03 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.474072+00
2771	2	2026-11-04 01:00:00+00	2026-11-04 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.474072+00
2772	2	2026-11-04 06:30:00+00	2026-11-04 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.474072+00
2773	2	2026-11-05 01:00:00+00	2026-11-05 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.474072+00
2774	2	2026-11-05 06:30:00+00	2026-11-05 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.474072+00
2775	2	2026-11-06 01:00:00+00	2026-11-06 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.474072+00
2776	2	2026-11-06 06:30:00+00	2026-11-06 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.474072+00
5519	4	2026-11-07 01:00:00+00	2026-11-07 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.714057+00
5520	4	2026-11-07 06:30:00+00	2026-11-07 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.714057+00
5521	4	2026-11-09 01:00:00+00	2026-11-09 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.714057+00
5522	4	2026-11-09 06:30:00+00	2026-11-09 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.714057+00
5523	4	2026-11-10 01:00:00+00	2026-11-10 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.714057+00
5524	4	2026-11-10 06:30:00+00	2026-11-10 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.714057+00
5525	4	2026-11-11 01:00:00+00	2026-11-11 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.714057+00
5526	4	2026-11-11 06:30:00+00	2026-11-11 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.714057+00
5527	4	2026-11-12 01:00:00+00	2026-11-12 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.714057+00
5528	4	2026-11-12 06:30:00+00	2026-11-12 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.714057+00
5529	4	2026-11-13 01:00:00+00	2026-11-13 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.714057+00
5530	4	2026-11-13 06:30:00+00	2026-11-13 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.714057+00
5531	4	2026-11-14 01:00:00+00	2026-11-14 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.714057+00
5532	4	2026-11-14 06:30:00+00	2026-11-14 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.714057+00
2813	4	2026-11-02 01:00:00+00	2026-11-02 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.484417+00
2814	4	2026-11-02 06:30:00+00	2026-11-02 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.484417+00
2815	4	2026-11-03 01:00:00+00	2026-11-03 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.484417+00
2816	4	2026-11-03 06:30:00+00	2026-11-03 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.484417+00
2817	4	2026-11-04 01:00:00+00	2026-11-04 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.484417+00
2818	4	2026-11-04 06:30:00+00	2026-11-04 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.484417+00
2819	4	2026-11-05 01:00:00+00	2026-11-05 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.484417+00
2820	4	2026-11-05 06:30:00+00	2026-11-05 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.484417+00
2821	4	2026-11-06 01:00:00+00	2026-11-06 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.484417+00
2822	4	2026-11-06 06:30:00+00	2026-11-06 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.484417+00
5533	4	2026-11-16 01:00:00+00	2026-11-16 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.714057+00
5534	4	2026-11-16 06:30:00+00	2026-11-16 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.714057+00
5535	4	2026-11-17 01:00:00+00	2026-11-17 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.714057+00
5536	4	2026-11-17 06:30:00+00	2026-11-17 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.714057+00
5537	4	2026-11-18 01:00:00+00	2026-11-18 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.714057+00
5538	4	2026-11-18 06:30:00+00	2026-11-18 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.714057+00
5539	4	2026-11-19 01:00:00+00	2026-11-19 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.714057+00
5540	4	2026-11-19 06:30:00+00	2026-11-19 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.714057+00
5541	4	2026-11-20 01:00:00+00	2026-11-20 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.714057+00
5542	4	2026-11-20 06:30:00+00	2026-11-20 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.714057+00
5543	4	2026-11-21 01:00:00+00	2026-11-21 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.714057+00
5544	4	2026-11-21 06:30:00+00	2026-11-21 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.714057+00
5617	8	2026-11-07 01:00:00+00	2026-11-07 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.736505+00
5618	8	2026-11-07 06:30:00+00	2026-11-07 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.736505+00
2859	6	2026-11-02 01:00:00+00	2026-11-02 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.494183+00
2860	6	2026-11-02 06:30:00+00	2026-11-02 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.494183+00
2861	6	2026-11-03 01:00:00+00	2026-11-03 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.494183+00
2862	6	2026-11-03 06:30:00+00	2026-11-03 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.494183+00
2863	6	2026-11-04 01:00:00+00	2026-11-04 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.494183+00
2864	6	2026-11-04 06:30:00+00	2026-11-04 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.494183+00
2865	6	2026-11-05 01:00:00+00	2026-11-05 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.494183+00
2866	6	2026-11-05 06:30:00+00	2026-11-05 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.494183+00
2867	6	2026-11-06 01:00:00+00	2026-11-06 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.494183+00
2868	6	2026-11-06 06:30:00+00	2026-11-06 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.494183+00
5619	8	2026-11-09 01:00:00+00	2026-11-09 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.736505+00
5620	8	2026-11-09 06:30:00+00	2026-11-09 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.736505+00
5621	8	2026-11-10 01:00:00+00	2026-11-10 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.736505+00
5622	8	2026-11-10 06:30:00+00	2026-11-10 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.736505+00
5623	8	2026-11-11 01:00:00+00	2026-11-11 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.736505+00
5624	8	2026-11-11 06:30:00+00	2026-11-11 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.736505+00
5625	8	2026-11-12 01:00:00+00	2026-11-12 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.736505+00
5626	8	2026-11-12 06:30:00+00	2026-11-12 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.736505+00
5627	8	2026-11-13 01:00:00+00	2026-11-13 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.736505+00
5628	8	2026-11-13 06:30:00+00	2026-11-13 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.736505+00
5629	8	2026-11-14 01:00:00+00	2026-11-14 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.736505+00
5630	8	2026-11-14 06:30:00+00	2026-11-14 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.736505+00
5631	8	2026-11-16 01:00:00+00	2026-11-16 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.736505+00
5632	8	2026-11-16 06:30:00+00	2026-11-16 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.736505+00
2905	8	2026-11-02 01:00:00+00	2026-11-02 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.503701+00
2906	8	2026-11-02 06:30:00+00	2026-11-02 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.503701+00
2907	8	2026-11-03 01:00:00+00	2026-11-03 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.503701+00
2908	8	2026-11-03 06:30:00+00	2026-11-03 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.503701+00
2909	8	2026-11-04 01:00:00+00	2026-11-04 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.503701+00
2910	8	2026-11-04 06:30:00+00	2026-11-04 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.503701+00
2911	8	2026-11-05 01:00:00+00	2026-11-05 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.503701+00
2912	8	2026-11-05 06:30:00+00	2026-11-05 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.503701+00
2913	8	2026-11-06 01:00:00+00	2026-11-06 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.503701+00
2914	8	2026-11-06 06:30:00+00	2026-11-06 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.503701+00
5633	8	2026-11-17 01:00:00+00	2026-11-17 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.736505+00
5634	8	2026-11-17 06:30:00+00	2026-11-17 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.736505+00
5635	8	2026-11-18 01:00:00+00	2026-11-18 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.736505+00
5636	8	2026-11-18 06:30:00+00	2026-11-18 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.736505+00
5637	8	2026-11-19 01:00:00+00	2026-11-19 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.736505+00
5638	8	2026-11-19 06:30:00+00	2026-11-19 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.736505+00
5639	8	2026-11-20 01:00:00+00	2026-11-20 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.736505+00
5640	8	2026-11-20 06:30:00+00	2026-11-20 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.736505+00
5641	8	2026-11-21 01:00:00+00	2026-11-21 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.736505+00
5642	8	2026-11-21 06:30:00+00	2026-11-21 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.736505+00
5715	12	2026-11-07 01:00:00+00	2026-11-07 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.759638+00
5716	12	2026-11-07 06:30:00+00	2026-11-07 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.759638+00
5717	12	2026-11-09 01:00:00+00	2026-11-09 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.759638+00
5718	12	2026-11-09 06:30:00+00	2026-11-09 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.759638+00
2951	10	2026-11-02 01:00:00+00	2026-11-02 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.513584+00
2952	10	2026-11-02 06:30:00+00	2026-11-02 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.513584+00
2953	10	2026-11-03 01:00:00+00	2026-11-03 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.513584+00
2954	10	2026-11-03 06:30:00+00	2026-11-03 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.513584+00
2955	10	2026-11-04 01:00:00+00	2026-11-04 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.513584+00
2956	10	2026-11-04 06:30:00+00	2026-11-04 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.513584+00
2957	10	2026-11-05 01:00:00+00	2026-11-05 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.513584+00
2958	10	2026-11-05 06:30:00+00	2026-11-05 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.513584+00
2959	10	2026-11-06 01:00:00+00	2026-11-06 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.513584+00
2960	10	2026-11-06 06:30:00+00	2026-11-06 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.513584+00
5719	12	2026-11-10 01:00:00+00	2026-11-10 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.759638+00
5720	12	2026-11-10 06:30:00+00	2026-11-10 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.759638+00
5721	12	2026-11-11 01:00:00+00	2026-11-11 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.759638+00
5722	12	2026-11-11 06:30:00+00	2026-11-11 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.759638+00
5723	12	2026-11-12 01:00:00+00	2026-11-12 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.759638+00
5724	12	2026-11-12 06:30:00+00	2026-11-12 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.759638+00
5725	12	2026-11-13 01:00:00+00	2026-11-13 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.759638+00
5726	12	2026-11-13 06:30:00+00	2026-11-13 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.759638+00
5727	12	2026-11-14 01:00:00+00	2026-11-14 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.759638+00
5728	12	2026-11-14 06:30:00+00	2026-11-14 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.759638+00
5729	12	2026-11-16 01:00:00+00	2026-11-16 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.759638+00
5730	12	2026-11-16 06:30:00+00	2026-11-16 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.759638+00
5731	12	2026-11-17 01:00:00+00	2026-11-17 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.759638+00
5732	12	2026-11-17 06:30:00+00	2026-11-17 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.759638+00
5706	11	2026-11-17 01:00:00+00	2026-11-17 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.754438+00
5707	11	2026-11-17 06:30:00+00	2026-11-17 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.754438+00
5708	11	2026-11-18 01:00:00+00	2026-11-18 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.754438+00
5709	11	2026-11-18 06:30:00+00	2026-11-18 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.754438+00
5710	11	2026-11-19 01:00:00+00	2026-11-19 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.754438+00
5711	11	2026-11-19 06:30:00+00	2026-11-19 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.754438+00
5712	11	2026-11-20 01:00:00+00	2026-11-20 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.754438+00
5713	11	2026-11-20 06:30:00+00	2026-11-20 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.754438+00
5714	11	2026-11-21 01:00:00+00	2026-11-21 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.754438+00
5790	15	2026-11-07 01:00:00+00	2026-11-07 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.773012+00
5791	15	2026-11-09 01:00:00+00	2026-11-09 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.773012+00
5792	15	2026-11-09 06:30:00+00	2026-11-09 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.773012+00
3021	13	2026-11-02 01:00:00+00	2026-11-02 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.529608+00
3022	13	2026-11-02 06:30:00+00	2026-11-02 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.529608+00
3023	13	2026-11-03 01:00:00+00	2026-11-03 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.529608+00
3024	13	2026-11-03 06:30:00+00	2026-11-03 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.529608+00
3025	13	2026-11-04 01:00:00+00	2026-11-04 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.529608+00
3026	13	2026-11-04 06:30:00+00	2026-11-04 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.529608+00
3027	13	2026-11-05 01:00:00+00	2026-11-05 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.529608+00
3028	13	2026-11-05 06:30:00+00	2026-11-05 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.529608+00
3029	13	2026-11-06 01:00:00+00	2026-11-06 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.529608+00
3030	13	2026-11-06 06:30:00+00	2026-11-06 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.529608+00
5793	15	2026-11-10 01:00:00+00	2026-11-10 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.773012+00
5794	15	2026-11-10 06:30:00+00	2026-11-10 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.773012+00
5795	15	2026-11-11 01:00:00+00	2026-11-11 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.773012+00
5796	15	2026-11-11 06:30:00+00	2026-11-11 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.773012+00
5797	15	2026-11-12 01:00:00+00	2026-11-12 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.773012+00
5798	15	2026-11-12 06:30:00+00	2026-11-12 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.773012+00
5799	15	2026-11-13 01:00:00+00	2026-11-13 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.773012+00
5800	15	2026-11-13 06:30:00+00	2026-11-13 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.773012+00
5801	15	2026-11-14 01:00:00+00	2026-11-14 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.773012+00
5802	15	2026-11-16 01:00:00+00	2026-11-16 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.773012+00
5803	15	2026-11-16 06:30:00+00	2026-11-16 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.773012+00
5804	15	2026-11-17 01:00:00+00	2026-11-17 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.773012+00
3067	15	2026-11-02 01:00:00+00	2026-11-02 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.538674+00
3068	15	2026-11-02 06:30:00+00	2026-11-02 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.538674+00
3069	15	2026-11-03 01:00:00+00	2026-11-03 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.538674+00
3070	15	2026-11-03 06:30:00+00	2026-11-03 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.538674+00
3071	15	2026-11-04 01:00:00+00	2026-11-04 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.538674+00
3072	15	2026-11-04 06:30:00+00	2026-11-04 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.538674+00
3073	15	2026-11-05 01:00:00+00	2026-11-05 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.538674+00
3074	15	2026-11-05 06:30:00+00	2026-11-05 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.538674+00
3075	15	2026-11-06 01:00:00+00	2026-11-06 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.538674+00
3076	15	2026-11-06 06:30:00+00	2026-11-06 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.538674+00
5805	15	2026-11-17 06:30:00+00	2026-11-17 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.773012+00
5806	15	2026-11-18 01:00:00+00	2026-11-18 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.773012+00
5807	15	2026-11-18 06:30:00+00	2026-11-18 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.773012+00
5808	15	2026-11-19 01:00:00+00	2026-11-19 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.773012+00
5809	15	2026-11-19 06:30:00+00	2026-11-19 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.773012+00
5810	15	2026-11-20 01:00:00+00	2026-11-20 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.773012+00
5811	15	2026-11-20 06:30:00+00	2026-11-20 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.773012+00
5812	15	2026-11-21 01:00:00+00	2026-11-21 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.773012+00
5888	19	2026-11-07 01:00:00+00	2026-11-07 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.790561+00
5889	19	2026-11-09 01:00:00+00	2026-11-09 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.790561+00
5890	19	2026-11-09 06:30:00+00	2026-11-09 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.790561+00
5891	19	2026-11-10 01:00:00+00	2026-11-10 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.790561+00
3113	17	2026-11-02 01:00:00+00	2026-11-02 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.545828+00
3114	17	2026-11-02 06:30:00+00	2026-11-02 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.545828+00
3115	17	2026-11-03 01:00:00+00	2026-11-03 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.545828+00
3116	17	2026-11-03 06:30:00+00	2026-11-03 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.545828+00
3117	17	2026-11-04 01:00:00+00	2026-11-04 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.545828+00
3118	17	2026-11-04 06:30:00+00	2026-11-04 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.545828+00
3119	17	2026-11-05 01:00:00+00	2026-11-05 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.545828+00
3120	17	2026-11-05 06:30:00+00	2026-11-05 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.545828+00
3121	17	2026-11-06 01:00:00+00	2026-11-06 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.545828+00
3122	17	2026-11-06 06:30:00+00	2026-11-06 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.545828+00
5892	19	2026-11-10 06:30:00+00	2026-11-10 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.790561+00
5893	19	2026-11-11 01:00:00+00	2026-11-11 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.790561+00
5894	19	2026-11-11 06:30:00+00	2026-11-11 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.790561+00
5895	19	2026-11-12 01:00:00+00	2026-11-12 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.790561+00
5896	19	2026-11-12 06:30:00+00	2026-11-12 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.790561+00
5897	19	2026-11-13 01:00:00+00	2026-11-13 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.790561+00
5898	19	2026-11-13 06:30:00+00	2026-11-13 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.790561+00
5899	19	2026-11-14 01:00:00+00	2026-11-14 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.790561+00
5900	19	2026-11-16 01:00:00+00	2026-11-16 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.790561+00
5901	19	2026-11-16 06:30:00+00	2026-11-16 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.790561+00
5902	19	2026-11-17 01:00:00+00	2026-11-17 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.790561+00
5903	19	2026-11-17 06:30:00+00	2026-11-17 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.790561+00
3159	19	2026-11-02 01:00:00+00	2026-11-02 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.554814+00
3160	19	2026-11-02 06:30:00+00	2026-11-02 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.554814+00
3161	19	2026-11-03 01:00:00+00	2026-11-03 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.554814+00
3162	19	2026-11-03 06:30:00+00	2026-11-03 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.554814+00
3163	19	2026-11-04 01:00:00+00	2026-11-04 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.554814+00
3164	19	2026-11-04 06:30:00+00	2026-11-04 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.554814+00
3165	19	2026-11-05 01:00:00+00	2026-11-05 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.554814+00
3166	19	2026-11-05 06:30:00+00	2026-11-05 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.554814+00
3167	19	2026-11-06 01:00:00+00	2026-11-06 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.554814+00
3168	19	2026-11-06 06:30:00+00	2026-11-06 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.554814+00
5904	19	2026-11-18 01:00:00+00	2026-11-18 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.790561+00
5905	19	2026-11-18 06:30:00+00	2026-11-18 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.790561+00
5906	19	2026-11-19 01:00:00+00	2026-11-19 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.790561+00
5907	19	2026-11-19 06:30:00+00	2026-11-19 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.790561+00
5908	19	2026-11-20 01:00:00+00	2026-11-20 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.790561+00
5909	19	2026-11-20 06:30:00+00	2026-11-20 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.790561+00
5910	19	2026-11-21 01:00:00+00	2026-11-21 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.790561+00
5986	24	2026-11-07 01:00:00+00	2026-11-07 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.8074+00
5987	24	2026-11-07 06:30:00+00	2026-11-07 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.8074+00
5988	24	2026-11-09 01:00:00+00	2026-11-09 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.8074+00
5989	24	2026-11-09 06:30:00+00	2026-11-09 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.8074+00
5990	24	2026-11-10 01:00:00+00	2026-11-10 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.8074+00
3205	21	2026-11-02 01:00:00+00	2026-11-02 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.563561+00
3206	21	2026-11-02 06:30:00+00	2026-11-02 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.563561+00
3207	21	2026-11-03 01:00:00+00	2026-11-03 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.563561+00
3208	21	2026-11-03 06:30:00+00	2026-11-03 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.563561+00
3209	21	2026-11-04 01:00:00+00	2026-11-04 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.563561+00
3210	21	2026-11-04 06:30:00+00	2026-11-04 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.563561+00
3211	21	2026-11-05 01:00:00+00	2026-11-05 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.563561+00
3212	21	2026-11-05 06:30:00+00	2026-11-05 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.563561+00
3213	21	2026-11-06 01:00:00+00	2026-11-06 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.563561+00
3214	21	2026-11-06 06:30:00+00	2026-11-06 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.563561+00
5991	24	2026-11-10 06:30:00+00	2026-11-10 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.8074+00
5992	24	2026-11-11 01:00:00+00	2026-11-11 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.8074+00
5993	24	2026-11-11 06:30:00+00	2026-11-11 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.8074+00
5994	24	2026-11-12 01:00:00+00	2026-11-12 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.8074+00
5995	24	2026-11-12 06:30:00+00	2026-11-12 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.8074+00
5996	24	2026-11-13 01:00:00+00	2026-11-13 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.8074+00
5997	24	2026-11-13 06:30:00+00	2026-11-13 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.8074+00
5998	24	2026-11-14 01:00:00+00	2026-11-14 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.8074+00
5999	24	2026-11-14 06:30:00+00	2026-11-14 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.8074+00
6000	24	2026-11-16 01:00:00+00	2026-11-16 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.8074+00
2997	12	2026-11-02 01:00:00+00	2026-11-02 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.523581+00
2998	12	2026-11-02 06:30:00+00	2026-11-02 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.523581+00
2999	12	2026-11-03 01:00:00+00	2026-11-03 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.523581+00
3000	12	2026-11-03 06:30:00+00	2026-11-03 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.523581+00
3001	12	2026-11-04 01:00:00+00	2026-11-04 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.523581+00
3002	12	2026-11-04 06:30:00+00	2026-11-04 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.523581+00
3003	12	2026-11-05 01:00:00+00	2026-11-05 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.523581+00
3004	12	2026-11-05 06:30:00+00	2026-11-05 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.523581+00
3005	12	2026-11-06 01:00:00+00	2026-11-06 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.523581+00
3006	12	2026-11-06 06:30:00+00	2026-11-06 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.523581+00
5733	12	2026-11-18 01:00:00+00	2026-11-18 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.759638+00
5734	12	2026-11-18 06:30:00+00	2026-11-18 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.759638+00
5735	12	2026-11-19 01:00:00+00	2026-11-19 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.759638+00
5736	12	2026-11-19 06:30:00+00	2026-11-19 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.759638+00
5737	12	2026-11-20 01:00:00+00	2026-11-20 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.759638+00
5738	12	2026-11-20 06:30:00+00	2026-11-20 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.759638+00
5739	12	2026-11-21 01:00:00+00	2026-11-21 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.759638+00
5740	12	2026-11-21 06:30:00+00	2026-11-21 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.759638+00
5813	16	2026-11-07 01:00:00+00	2026-11-07 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.778005+00
5814	16	2026-11-07 06:30:00+00	2026-11-07 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.778005+00
5815	16	2026-11-09 01:00:00+00	2026-11-09 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.778005+00
5816	16	2026-11-09 06:30:00+00	2026-11-09 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.778005+00
5817	16	2026-11-10 01:00:00+00	2026-11-10 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.778005+00
5818	16	2026-11-10 06:30:00+00	2026-11-10 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.778005+00
3043	14	2026-11-02 01:00:00+00	2026-11-02 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.534275+00
3044	14	2026-11-02 06:30:00+00	2026-11-02 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.534275+00
3045	14	2026-11-03 01:00:00+00	2026-11-03 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.534275+00
3046	14	2026-11-03 06:30:00+00	2026-11-03 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.534275+00
3047	14	2026-11-04 01:00:00+00	2026-11-04 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.534275+00
3048	14	2026-11-04 06:30:00+00	2026-11-04 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.534275+00
3049	14	2026-11-05 01:00:00+00	2026-11-05 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.534275+00
3050	14	2026-11-05 06:30:00+00	2026-11-05 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.534275+00
3051	14	2026-11-06 01:00:00+00	2026-11-06 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.534275+00
3052	14	2026-11-06 06:30:00+00	2026-11-06 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.534275+00
5819	16	2026-11-11 01:00:00+00	2026-11-11 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.778005+00
5820	16	2026-11-11 06:30:00+00	2026-11-11 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.778005+00
5821	16	2026-11-12 01:00:00+00	2026-11-12 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.778005+00
5822	16	2026-11-12 06:30:00+00	2026-11-12 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.778005+00
5823	16	2026-11-13 01:00:00+00	2026-11-13 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.778005+00
5824	16	2026-11-13 06:30:00+00	2026-11-13 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.778005+00
5825	16	2026-11-14 01:00:00+00	2026-11-14 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.778005+00
5826	16	2026-11-14 06:30:00+00	2026-11-14 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.778005+00
5827	16	2026-11-16 01:00:00+00	2026-11-16 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.778005+00
5828	16	2026-11-16 06:30:00+00	2026-11-16 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.778005+00
5829	16	2026-11-17 01:00:00+00	2026-11-17 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.778005+00
5830	16	2026-11-17 06:30:00+00	2026-11-17 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.778005+00
5831	16	2026-11-18 01:00:00+00	2026-11-18 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.778005+00
5832	16	2026-11-18 06:30:00+00	2026-11-18 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.778005+00
3089	16	2026-11-02 01:00:00+00	2026-11-02 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.5424+00
3090	16	2026-11-02 06:30:00+00	2026-11-02 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.5424+00
3091	16	2026-11-03 01:00:00+00	2026-11-03 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.5424+00
3092	16	2026-11-03 06:30:00+00	2026-11-03 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.5424+00
3093	16	2026-11-04 01:00:00+00	2026-11-04 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.5424+00
3094	16	2026-11-04 06:30:00+00	2026-11-04 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.5424+00
3095	16	2026-11-05 01:00:00+00	2026-11-05 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.5424+00
3096	16	2026-11-05 06:30:00+00	2026-11-05 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.5424+00
3097	16	2026-11-06 01:00:00+00	2026-11-06 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.5424+00
3098	16	2026-11-06 06:30:00+00	2026-11-06 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.5424+00
5833	16	2026-11-19 01:00:00+00	2026-11-19 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.778005+00
5834	16	2026-11-19 06:30:00+00	2026-11-19 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.778005+00
5835	16	2026-11-20 01:00:00+00	2026-11-20 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.778005+00
5836	16	2026-11-20 06:30:00+00	2026-11-20 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.778005+00
5837	16	2026-11-21 01:00:00+00	2026-11-21 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.778005+00
5838	16	2026-11-21 06:30:00+00	2026-11-21 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.778005+00
5911	20	2026-11-07 01:00:00+00	2026-11-07 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.794617+00
5912	20	2026-11-07 06:30:00+00	2026-11-07 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.794617+00
5913	20	2026-11-09 01:00:00+00	2026-11-09 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.794617+00
5914	20	2026-11-09 06:30:00+00	2026-11-09 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.794617+00
5915	20	2026-11-10 01:00:00+00	2026-11-10 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.794617+00
5916	20	2026-11-10 06:30:00+00	2026-11-10 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.794617+00
5917	20	2026-11-11 01:00:00+00	2026-11-11 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.794617+00
5918	20	2026-11-11 06:30:00+00	2026-11-11 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.794617+00
3135	18	2026-11-02 01:00:00+00	2026-11-02 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.550663+00
3136	18	2026-11-02 06:30:00+00	2026-11-02 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.550663+00
3137	18	2026-11-03 01:00:00+00	2026-11-03 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.550663+00
3138	18	2026-11-03 06:30:00+00	2026-11-03 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.550663+00
3139	18	2026-11-04 01:00:00+00	2026-11-04 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.550663+00
3140	18	2026-11-04 06:30:00+00	2026-11-04 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.550663+00
3141	18	2026-11-05 01:00:00+00	2026-11-05 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.550663+00
3142	18	2026-11-05 06:30:00+00	2026-11-05 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.550663+00
3143	18	2026-11-06 01:00:00+00	2026-11-06 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.550663+00
3144	18	2026-11-06 06:30:00+00	2026-11-06 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.550663+00
5919	20	2026-11-12 01:00:00+00	2026-11-12 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.794617+00
5920	20	2026-11-12 06:30:00+00	2026-11-12 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.794617+00
5921	20	2026-11-13 01:00:00+00	2026-11-13 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.794617+00
5922	20	2026-11-13 06:30:00+00	2026-11-13 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.794617+00
5923	20	2026-11-14 01:00:00+00	2026-11-14 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.794617+00
5924	20	2026-11-14 06:30:00+00	2026-11-14 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.794617+00
5925	20	2026-11-16 01:00:00+00	2026-11-16 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.794617+00
5926	20	2026-11-16 06:30:00+00	2026-11-16 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.794617+00
5927	20	2026-11-17 01:00:00+00	2026-11-17 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.794617+00
5928	20	2026-11-17 06:30:00+00	2026-11-17 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.794617+00
5929	20	2026-11-18 01:00:00+00	2026-11-18 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.794617+00
5930	20	2026-11-18 06:30:00+00	2026-11-18 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.794617+00
5931	20	2026-11-19 01:00:00+00	2026-11-19 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.794617+00
5932	20	2026-11-19 06:30:00+00	2026-11-19 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.794617+00
3181	20	2026-11-02 01:00:00+00	2026-11-02 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.559446+00
3182	20	2026-11-02 06:30:00+00	2026-11-02 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.559446+00
3183	20	2026-11-03 01:00:00+00	2026-11-03 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.559446+00
3184	20	2026-11-03 06:30:00+00	2026-11-03 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.559446+00
3185	20	2026-11-04 01:00:00+00	2026-11-04 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.559446+00
3186	20	2026-11-04 06:30:00+00	2026-11-04 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.559446+00
3187	20	2026-11-05 01:00:00+00	2026-11-05 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.559446+00
3188	20	2026-11-05 06:30:00+00	2026-11-05 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.559446+00
3189	20	2026-11-06 01:00:00+00	2026-11-06 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.559446+00
3190	20	2026-11-06 06:30:00+00	2026-11-06 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.559446+00
5933	20	2026-11-20 01:00:00+00	2026-11-20 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.794617+00
5934	20	2026-11-20 06:30:00+00	2026-11-20 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.794617+00
5935	20	2026-11-21 01:00:00+00	2026-11-21 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.794617+00
5936	20	2026-11-21 06:30:00+00	2026-11-21 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.794617+00
6012	25	2026-11-07 01:00:00+00	2026-11-07 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.812498+00
6013	25	2026-11-09 01:00:00+00	2026-11-09 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.812498+00
6014	25	2026-11-09 06:30:00+00	2026-11-09 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.812498+00
6015	25	2026-11-10 01:00:00+00	2026-11-10 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.812498+00
6016	25	2026-11-10 06:30:00+00	2026-11-10 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.812498+00
6017	25	2026-11-11 01:00:00+00	2026-11-11 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.812498+00
6018	25	2026-11-11 06:30:00+00	2026-11-11 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.812498+00
6019	25	2026-11-12 01:00:00+00	2026-11-12 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.812498+00
6020	25	2026-11-12 06:30:00+00	2026-11-12 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.812498+00
6021	25	2026-11-13 01:00:00+00	2026-11-13 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.812498+00
5844	17	2026-11-11 01:00:00+00	2026-11-11 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.782797+00
5845	17	2026-11-11 06:30:00+00	2026-11-11 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.782797+00
3251	23	2026-11-02 01:00:00+00	2026-11-02 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.572505+00
3252	23	2026-11-02 06:30:00+00	2026-11-02 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.572505+00
3253	23	2026-11-03 01:00:00+00	2026-11-03 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.572505+00
3254	23	2026-11-03 06:30:00+00	2026-11-03 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.572505+00
3255	23	2026-11-04 01:00:00+00	2026-11-04 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.572505+00
3256	23	2026-11-04 06:30:00+00	2026-11-04 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.572505+00
3257	23	2026-11-05 01:00:00+00	2026-11-05 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.572505+00
3258	23	2026-11-05 06:30:00+00	2026-11-05 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.572505+00
3259	23	2026-11-06 01:00:00+00	2026-11-06 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.572505+00
3260	23	2026-11-06 06:30:00+00	2026-11-06 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.572505+00
5846	17	2026-11-12 01:00:00+00	2026-11-12 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.782797+00
5847	17	2026-11-12 06:30:00+00	2026-11-12 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.782797+00
5848	17	2026-11-13 01:00:00+00	2026-11-13 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.782797+00
5849	17	2026-11-13 06:30:00+00	2026-11-13 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.782797+00
5850	17	2026-11-14 01:00:00+00	2026-11-14 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.782797+00
5851	17	2026-11-16 01:00:00+00	2026-11-16 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.782797+00
5852	17	2026-11-16 06:30:00+00	2026-11-16 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.782797+00
5853	17	2026-11-17 01:00:00+00	2026-11-17 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.782797+00
5854	17	2026-11-17 06:30:00+00	2026-11-17 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.782797+00
5855	17	2026-11-18 01:00:00+00	2026-11-18 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.782797+00
5856	17	2026-11-18 06:30:00+00	2026-11-18 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.782797+00
5857	17	2026-11-19 01:00:00+00	2026-11-19 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.782797+00
3297	25	2026-11-02 01:00:00+00	2026-11-02 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.580914+00
3298	25	2026-11-02 06:30:00+00	2026-11-02 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.580914+00
3299	25	2026-11-03 01:00:00+00	2026-11-03 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.580914+00
3300	25	2026-11-03 06:30:00+00	2026-11-03 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.580914+00
3301	25	2026-11-04 01:00:00+00	2026-11-04 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.580914+00
3302	25	2026-11-04 06:30:00+00	2026-11-04 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.580914+00
3303	25	2026-11-05 01:00:00+00	2026-11-05 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.580914+00
3304	25	2026-11-05 06:30:00+00	2026-11-05 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.580914+00
3305	25	2026-11-06 01:00:00+00	2026-11-06 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.580914+00
3306	25	2026-11-06 06:30:00+00	2026-11-06 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.580914+00
5858	17	2026-11-19 06:30:00+00	2026-11-19 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.782797+00
5859	17	2026-11-20 01:00:00+00	2026-11-20 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.782797+00
5860	17	2026-11-20 06:30:00+00	2026-11-20 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.782797+00
5861	17	2026-11-21 01:00:00+00	2026-11-21 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.782797+00
5937	21	2026-11-07 01:00:00+00	2026-11-07 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.799046+00
5938	21	2026-11-09 01:00:00+00	2026-11-09 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.799046+00
5939	21	2026-11-09 06:30:00+00	2026-11-09 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.799046+00
5940	21	2026-11-10 01:00:00+00	2026-11-10 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.799046+00
5941	21	2026-11-10 06:30:00+00	2026-11-10 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.799046+00
5942	21	2026-11-11 01:00:00+00	2026-11-11 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.799046+00
5943	21	2026-11-11 06:30:00+00	2026-11-11 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.799046+00
5944	21	2026-11-12 01:00:00+00	2026-11-12 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.799046+00
3343	27	2026-11-02 01:00:00+00	2026-11-02 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.590169+00
3344	27	2026-11-02 06:30:00+00	2026-11-02 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.590169+00
3345	27	2026-11-03 01:00:00+00	2026-11-03 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.590169+00
3346	27	2026-11-03 06:30:00+00	2026-11-03 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.590169+00
3347	27	2026-11-04 01:00:00+00	2026-11-04 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.590169+00
3348	27	2026-11-04 06:30:00+00	2026-11-04 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.590169+00
3349	27	2026-11-05 01:00:00+00	2026-11-05 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.590169+00
3350	27	2026-11-05 06:30:00+00	2026-11-05 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.590169+00
3351	27	2026-11-06 01:00:00+00	2026-11-06 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.590169+00
3352	27	2026-11-06 06:30:00+00	2026-11-06 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.590169+00
5945	21	2026-11-12 06:30:00+00	2026-11-12 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.799046+00
5946	21	2026-11-13 01:00:00+00	2026-11-13 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.799046+00
5947	21	2026-11-13 06:30:00+00	2026-11-13 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.799046+00
5948	21	2026-11-14 01:00:00+00	2026-11-14 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.799046+00
5949	21	2026-11-16 01:00:00+00	2026-11-16 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.799046+00
5950	21	2026-11-16 06:30:00+00	2026-11-16 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.799046+00
5951	21	2026-11-17 01:00:00+00	2026-11-17 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.799046+00
5952	21	2026-11-17 06:30:00+00	2026-11-17 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.799046+00
5953	21	2026-11-18 01:00:00+00	2026-11-18 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.799046+00
5954	21	2026-11-18 06:30:00+00	2026-11-18 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.799046+00
5955	21	2026-11-19 01:00:00+00	2026-11-19 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.799046+00
5956	21	2026-11-19 06:30:00+00	2026-11-19 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.799046+00
3227	22	2026-11-02 01:00:00+00	2026-11-02 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.568356+00
3228	22	2026-11-02 06:30:00+00	2026-11-02 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.568356+00
3229	22	2026-11-03 01:00:00+00	2026-11-03 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.568356+00
3230	22	2026-11-03 06:30:00+00	2026-11-03 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.568356+00
3231	22	2026-11-04 01:00:00+00	2026-11-04 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.568356+00
3232	22	2026-11-04 06:30:00+00	2026-11-04 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.568356+00
3233	22	2026-11-05 01:00:00+00	2026-11-05 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.568356+00
3234	22	2026-11-05 06:30:00+00	2026-11-05 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.568356+00
3235	22	2026-11-06 01:00:00+00	2026-11-06 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.568356+00
3236	22	2026-11-06 06:30:00+00	2026-11-06 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.568356+00
5867	18	2026-11-10 06:30:00+00	2026-11-10 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.786698+00
5868	18	2026-11-11 01:00:00+00	2026-11-11 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.786698+00
5869	18	2026-11-11 06:30:00+00	2026-11-11 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.786698+00
5870	18	2026-11-12 01:00:00+00	2026-11-12 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.786698+00
5871	18	2026-11-12 06:30:00+00	2026-11-12 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.786698+00
5872	18	2026-11-13 01:00:00+00	2026-11-13 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.786698+00
5873	18	2026-11-13 06:30:00+00	2026-11-13 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.786698+00
5874	18	2026-11-14 01:00:00+00	2026-11-14 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.786698+00
5875	18	2026-11-14 06:30:00+00	2026-11-14 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.786698+00
5876	18	2026-11-16 01:00:00+00	2026-11-16 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.786698+00
5877	18	2026-11-16 06:30:00+00	2026-11-16 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.786698+00
5878	18	2026-11-17 01:00:00+00	2026-11-17 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.786698+00
5879	18	2026-11-17 06:30:00+00	2026-11-17 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.786698+00
5880	18	2026-11-18 01:00:00+00	2026-11-18 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.786698+00
3273	24	2026-11-02 01:00:00+00	2026-11-02 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.5768+00
3274	24	2026-11-02 06:30:00+00	2026-11-02 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.5768+00
3275	24	2026-11-03 01:00:00+00	2026-11-03 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.5768+00
2059	1	2026-10-31 01:00:00+00	2026-10-31 04:30:00+00	\N	t	ERP	2026-10-31 11:59:00.838927+00
2180	6	2026-10-31 01:00:00+00	2026-10-31 04:30:00+00	\N	t	ERP	2026-10-31 11:59:00.871868+00
2181	6	2026-10-31 06:30:00+00	2026-10-31 10:00:00+00	\N	t	ERP	2026-10-31 11:59:00.871868+00
2304	11	2026-10-31 01:00:00+00	2026-10-31 04:30:00+00	\N	t	ERP	2026-10-31 11:59:00.895521+00
2425	16	2026-10-31 01:00:00+00	2026-10-31 04:30:00+00	\N	t	ERP	2026-10-31 11:59:00.913576+00
2426	16	2026-10-31 06:30:00+00	2026-10-31 10:00:00+00	\N	t	ERP	2026-10-31 11:59:00.913576+00
3276	24	2026-11-03 06:30:00+00	2026-11-03 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.5768+00
3277	24	2026-11-04 01:00:00+00	2026-11-04 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.5768+00
3278	24	2026-11-04 06:30:00+00	2026-11-04 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.5768+00
3279	24	2026-11-05 01:00:00+00	2026-11-05 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.5768+00
3280	24	2026-11-05 06:30:00+00	2026-11-05 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.5768+00
3281	24	2026-11-06 01:00:00+00	2026-11-06 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.5768+00
3282	24	2026-11-06 06:30:00+00	2026-11-06 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.5768+00
5881	18	2026-11-18 06:30:00+00	2026-11-18 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.786698+00
5882	18	2026-11-19 01:00:00+00	2026-11-19 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.786698+00
5883	18	2026-11-19 06:30:00+00	2026-11-19 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.786698+00
5884	18	2026-11-20 01:00:00+00	2026-11-20 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.786698+00
5885	18	2026-11-20 06:30:00+00	2026-11-20 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.786698+00
5886	18	2026-11-21 01:00:00+00	2026-11-21 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.786698+00
5887	18	2026-11-21 06:30:00+00	2026-11-21 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.786698+00
2082	2	2026-10-31 01:00:00+00	2026-10-31 04:30:00+00	\N	t	ERP	2026-10-31 11:59:00.846925+00
2083	2	2026-10-31 06:30:00+00	2026-10-31 10:00:00+00	\N	t	ERP	2026-10-31 11:59:00.846925+00
2206	7	2026-10-31 01:00:00+00	2026-10-31 04:30:00+00	\N	t	ERP	2026-10-31 11:59:00.876797+00
2327	12	2026-10-31 01:00:00+00	2026-10-31 04:30:00+00	\N	t	ERP	2026-10-31 11:59:00.89933+00
2328	12	2026-10-31 06:30:00+00	2026-10-31 10:00:00+00	\N	t	ERP	2026-10-31 11:59:00.89933+00
2451	17	2026-10-31 01:00:00+00	2026-10-31 04:30:00+00	\N	t	ERP	2026-10-31 11:59:00.917301+00
5960	22	2026-11-07 01:00:00+00	2026-11-07 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.803421+00
5961	22	2026-11-07 06:30:00+00	2026-11-07 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.803421+00
5962	22	2026-11-09 01:00:00+00	2026-11-09 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.803421+00
5963	22	2026-11-09 06:30:00+00	2026-11-09 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.803421+00
5964	22	2026-11-10 01:00:00+00	2026-11-10 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.803421+00
5965	22	2026-11-10 06:30:00+00	2026-11-10 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.803421+00
5966	22	2026-11-11 01:00:00+00	2026-11-11 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.803421+00
5967	22	2026-11-11 06:30:00+00	2026-11-11 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.803421+00
5968	22	2026-11-12 01:00:00+00	2026-11-12 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.803421+00
5969	22	2026-11-12 06:30:00+00	2026-11-12 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.803421+00
5970	22	2026-11-13 01:00:00+00	2026-11-13 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.803421+00
2572	22	2026-10-31 01:00:00+00	2026-10-31 04:30:00+00	\N	t	ERP	2026-10-31 11:59:00.936224+00
2573	22	2026-10-31 06:30:00+00	2026-10-31 10:00:00+00	\N	t	ERP	2026-10-31 11:59:00.936224+00
5971	22	2026-11-13 06:30:00+00	2026-11-13 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.803421+00
5972	22	2026-11-14 01:00:00+00	2026-11-14 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.803421+00
5973	22	2026-11-14 06:30:00+00	2026-11-14 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.803421+00
5974	22	2026-11-16 01:00:00+00	2026-11-16 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.803421+00
5975	22	2026-11-16 06:30:00+00	2026-11-16 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.803421+00
5976	22	2026-11-17 01:00:00+00	2026-11-17 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.803421+00
2108	3	2026-10-31 01:00:00+00	2026-10-31 04:30:00+00	\N	t	ERP	2026-10-31 11:59:00.85413+00
2229	8	2026-10-31 01:00:00+00	2026-10-31 04:30:00+00	\N	t	ERP	2026-10-31 11:59:00.881631+00
2230	8	2026-10-31 06:30:00+00	2026-10-31 10:00:00+00	\N	t	ERP	2026-10-31 11:59:00.881631+00
2353	13	2026-10-31 01:00:00+00	2026-10-31 04:30:00+00	\N	t	ERP	2026-10-31 11:59:00.903161+00
2474	18	2026-10-31 01:00:00+00	2026-10-31 04:30:00+00	\N	t	ERP	2026-10-31 11:59:00.921132+00
2475	18	2026-10-31 06:30:00+00	2026-10-31 10:00:00+00	\N	t	ERP	2026-10-31 11:59:00.921132+00
5957	21	2026-11-20 01:00:00+00	2026-11-20 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.799046+00
5958	21	2026-11-20 06:30:00+00	2026-11-20 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.799046+00
5959	21	2026-11-21 01:00:00+00	2026-11-21 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.799046+00
6035	26	2026-11-07 01:00:00+00	2026-11-07 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.817166+00
6036	26	2026-11-07 06:30:00+00	2026-11-07 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.817166+00
6037	26	2026-11-09 01:00:00+00	2026-11-09 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.817166+00
6038	26	2026-11-09 06:30:00+00	2026-11-09 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.817166+00
6039	26	2026-11-10 01:00:00+00	2026-11-10 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.817166+00
6040	26	2026-11-10 06:30:00+00	2026-11-10 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.817166+00
6041	26	2026-11-11 01:00:00+00	2026-11-11 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.817166+00
6042	26	2026-11-11 06:30:00+00	2026-11-11 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.817166+00
6043	26	2026-11-12 01:00:00+00	2026-11-12 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.817166+00
6044	26	2026-11-12 06:30:00+00	2026-11-12 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.817166+00
6045	26	2026-11-13 01:00:00+00	2026-11-13 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.817166+00
6046	26	2026-11-13 06:30:00+00	2026-11-13 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.817166+00
6047	26	2026-11-14 01:00:00+00	2026-11-14 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.817166+00
6048	26	2026-11-14 06:30:00+00	2026-11-14 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.817166+00
6049	26	2026-11-16 01:00:00+00	2026-11-16 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.817166+00
6050	26	2026-11-16 06:30:00+00	2026-11-16 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.817166+00
6051	26	2026-11-17 01:00:00+00	2026-11-17 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.817166+00
6052	26	2026-11-17 06:30:00+00	2026-11-17 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.817166+00
6053	26	2026-11-18 01:00:00+00	2026-11-18 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.817166+00
6054	26	2026-11-18 06:30:00+00	2026-11-18 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.817166+00
6055	26	2026-11-19 01:00:00+00	2026-11-19 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.817166+00
3319	26	2026-11-02 01:00:00+00	2026-11-02 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.58566+00
3320	26	2026-11-02 06:30:00+00	2026-11-02 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.58566+00
3321	26	2026-11-03 01:00:00+00	2026-11-03 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.58566+00
3322	26	2026-11-03 06:30:00+00	2026-11-03 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.58566+00
3323	26	2026-11-04 01:00:00+00	2026-11-04 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.58566+00
3324	26	2026-11-04 06:30:00+00	2026-11-04 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.58566+00
3325	26	2026-11-05 01:00:00+00	2026-11-05 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.58566+00
3326	26	2026-11-05 06:30:00+00	2026-11-05 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.58566+00
3327	26	2026-11-06 01:00:00+00	2026-11-06 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.58566+00
3328	26	2026-11-06 06:30:00+00	2026-11-06 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.58566+00
6056	26	2026-11-19 06:30:00+00	2026-11-19 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.817166+00
6057	26	2026-11-20 01:00:00+00	2026-11-20 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.817166+00
6058	26	2026-11-20 06:30:00+00	2026-11-20 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.817166+00
6059	26	2026-11-21 01:00:00+00	2026-11-21 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.817166+00
6060	26	2026-11-21 06:30:00+00	2026-11-21 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.817166+00
2131	4	2026-10-31 01:00:00+00	2026-10-31 04:30:00+00	\N	t	ERP	2026-10-31 11:59:00.860377+00
2132	4	2026-10-31 06:30:00+00	2026-10-31 10:00:00+00	\N	t	ERP	2026-10-31 11:59:00.860377+00
2255	9	2026-10-31 01:00:00+00	2026-10-31 04:30:00+00	\N	t	ERP	2026-10-31 11:59:00.886367+00
2376	14	2026-10-31 01:00:00+00	2026-10-31 04:30:00+00	\N	t	ERP	2026-10-31 11:59:00.906752+00
2377	14	2026-10-31 06:30:00+00	2026-10-31 10:00:00+00	\N	t	ERP	2026-10-31 11:59:00.906752+00
2500	19	2026-10-31 01:00:00+00	2026-10-31 04:30:00+00	\N	t	ERP	2026-10-31 11:59:00.924628+00
2621	24	2026-10-31 01:00:00+00	2026-10-31 04:30:00+00	\N	t	ERP	2026-10-31 11:59:00.944058+00
2622	24	2026-10-31 06:30:00+00	2026-10-31 10:00:00+00	\N	t	ERP	2026-10-31 11:59:00.944058+00
2157	5	2026-10-31 01:00:00+00	2026-10-31 04:30:00+00	\N	t	ERP	2026-10-31 11:59:00.866474+00
2278	10	2026-10-31 01:00:00+00	2026-10-31 04:30:00+00	\N	t	ERP	2026-10-31 11:59:00.890965+00
2279	10	2026-10-31 06:30:00+00	2026-10-31 10:00:00+00	\N	t	ERP	2026-10-31 11:59:00.890965+00
2402	15	2026-10-31 01:00:00+00	2026-10-31 04:30:00+00	\N	t	ERP	2026-10-31 11:59:00.910266+00
2523	20	2026-10-31 01:00:00+00	2026-10-31 04:30:00+00	\N	t	ERP	2026-10-31 11:59:00.928115+00
2524	20	2026-10-31 06:30:00+00	2026-10-31 10:00:00+00	\N	t	ERP	2026-10-31 11:59:00.928115+00
2647	25	2026-10-31 01:00:00+00	2026-10-31 04:30:00+00	\N	t	ERP	2026-10-31 11:59:00.94812+00
2549	21	2026-10-31 01:00:00+00	2026-10-31 04:30:00+00	\N	t	ERP	2026-10-31 11:59:00.932095+00
2670	26	2026-10-31 01:00:00+00	2026-10-31 04:30:00+00	\N	t	ERP	2026-10-31 11:59:00.951988+00
2671	26	2026-10-31 06:30:00+00	2026-10-31 10:00:00+00	\N	t	ERP	2026-10-31 11:59:00.951988+00
5977	22	2026-11-17 06:30:00+00	2026-11-17 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.803421+00
5978	22	2026-11-18 01:00:00+00	2026-11-18 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.803421+00
5979	22	2026-11-18 06:30:00+00	2026-11-18 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.803421+00
5980	22	2026-11-19 01:00:00+00	2026-11-19 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.803421+00
5981	22	2026-11-19 06:30:00+00	2026-11-19 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.803421+00
5982	22	2026-11-20 01:00:00+00	2026-11-20 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.803421+00
5983	22	2026-11-20 06:30:00+00	2026-11-20 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.803421+00
5984	22	2026-11-21 01:00:00+00	2026-11-21 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.803421+00
5985	22	2026-11-21 06:30:00+00	2026-11-21 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.803421+00
3365	28	2026-11-02 01:00:00+00	2026-11-02 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.594894+00
3366	28	2026-11-02 06:30:00+00	2026-11-02 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.594894+00
3367	28	2026-11-03 01:00:00+00	2026-11-03 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.594894+00
3368	28	2026-11-03 06:30:00+00	2026-11-03 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.594894+00
3369	28	2026-11-04 01:00:00+00	2026-11-04 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.594894+00
3370	28	2026-11-04 06:30:00+00	2026-11-04 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.594894+00
3371	28	2026-11-05 01:00:00+00	2026-11-05 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.594894+00
3372	28	2026-11-05 06:30:00+00	2026-11-05 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.594894+00
3373	28	2026-11-06 01:00:00+00	2026-11-06 04:30:00+00	\N	t	ERP	2026-11-01 05:53:20.594894+00
3374	28	2026-11-06 06:30:00+00	2026-11-06 10:00:00+00	\N	t	ERP	2026-11-01 05:53:20.594894+00
6061	23	2026-11-07 01:00:00+00	2026-11-07 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.820946+00
6062	23	2026-11-09 01:00:00+00	2026-11-09 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.820946+00
6063	23	2026-11-09 06:30:00+00	2026-11-09 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.820946+00
6064	23	2026-11-10 01:00:00+00	2026-11-10 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.820946+00
6065	23	2026-11-10 06:30:00+00	2026-11-10 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.820946+00
6066	23	2026-11-11 01:00:00+00	2026-11-11 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.820946+00
6067	23	2026-11-11 06:30:00+00	2026-11-11 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.820946+00
6068	23	2026-11-12 01:00:00+00	2026-11-12 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.820946+00
6069	23	2026-11-12 06:30:00+00	2026-11-12 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.820946+00
6070	23	2026-11-13 01:00:00+00	2026-11-13 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.820946+00
6071	23	2026-11-13 06:30:00+00	2026-11-13 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.820946+00
6072	23	2026-11-14 01:00:00+00	2026-11-14 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.820946+00
6073	23	2026-11-16 01:00:00+00	2026-11-16 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.820946+00
6074	23	2026-11-16 06:30:00+00	2026-11-16 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.820946+00
6075	23	2026-11-17 01:00:00+00	2026-11-17 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.820946+00
6076	23	2026-11-17 06:30:00+00	2026-11-17 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.820946+00
6077	23	2026-11-18 01:00:00+00	2026-11-18 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.820946+00
6078	23	2026-11-18 06:30:00+00	2026-11-18 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.820946+00
6079	23	2026-11-19 01:00:00+00	2026-11-19 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.820946+00
6080	23	2026-11-19 06:30:00+00	2026-11-19 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.820946+00
6081	23	2026-11-20 01:00:00+00	2026-11-20 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.820946+00
6082	23	2026-11-20 06:30:00+00	2026-11-20 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.820946+00
6083	23	2026-11-21 01:00:00+00	2026-11-21 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.820946+00
2696	27	2026-10-31 01:00:00+00	2026-10-31 04:30:00+00	\N	t	ERP	2026-10-31 11:59:00.956058+00
6001	24	2026-11-16 06:30:00+00	2026-11-16 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.8074+00
6002	24	2026-11-17 01:00:00+00	2026-11-17 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.8074+00
6003	24	2026-11-17 06:30:00+00	2026-11-17 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.8074+00
6004	24	2026-11-18 01:00:00+00	2026-11-18 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.8074+00
6005	24	2026-11-18 06:30:00+00	2026-11-18 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.8074+00
6006	24	2026-11-19 01:00:00+00	2026-11-19 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.8074+00
6007	24	2026-11-19 06:30:00+00	2026-11-19 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.8074+00
6008	24	2026-11-20 01:00:00+00	2026-11-20 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.8074+00
6009	24	2026-11-20 06:30:00+00	2026-11-20 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.8074+00
6010	24	2026-11-21 01:00:00+00	2026-11-21 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.8074+00
6011	24	2026-11-21 06:30:00+00	2026-11-21 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.8074+00
6084	27	2026-11-07 01:00:00+00	2026-11-07 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.824629+00
6085	27	2026-11-09 01:00:00+00	2026-11-09 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.824629+00
6086	27	2026-11-09 06:30:00+00	2026-11-09 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.824629+00
6087	27	2026-11-10 01:00:00+00	2026-11-10 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.824629+00
6088	27	2026-11-10 06:30:00+00	2026-11-10 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.824629+00
6089	27	2026-11-11 01:00:00+00	2026-11-11 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.824629+00
6090	27	2026-11-11 06:30:00+00	2026-11-11 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.824629+00
6091	27	2026-11-12 01:00:00+00	2026-11-12 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.824629+00
6092	27	2026-11-12 06:30:00+00	2026-11-12 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.824629+00
6093	27	2026-11-13 01:00:00+00	2026-11-13 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.824629+00
6094	27	2026-11-13 06:30:00+00	2026-11-13 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.824629+00
6095	27	2026-11-14 01:00:00+00	2026-11-14 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.824629+00
6096	27	2026-11-16 01:00:00+00	2026-11-16 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.824629+00
6097	27	2026-11-16 06:30:00+00	2026-11-16 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.824629+00
6098	27	2026-11-17 01:00:00+00	2026-11-17 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.824629+00
6099	27	2026-11-17 06:30:00+00	2026-11-17 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.824629+00
6100	27	2026-11-18 01:00:00+00	2026-11-18 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.824629+00
6101	27	2026-11-18 06:30:00+00	2026-11-18 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.824629+00
6102	27	2026-11-19 01:00:00+00	2026-11-19 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.824629+00
6103	27	2026-11-19 06:30:00+00	2026-11-19 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.824629+00
6104	27	2026-11-20 01:00:00+00	2026-11-20 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.824629+00
6105	27	2026-11-20 06:30:00+00	2026-11-20 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.824629+00
6106	27	2026-11-21 01:00:00+00	2026-11-21 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.824629+00
2598	23	2026-10-31 01:00:00+00	2026-10-31 04:30:00+00	\N	t	ERP	2026-10-31 11:59:00.94015+00
6022	25	2026-11-13 06:30:00+00	2026-11-13 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.812498+00
6023	25	2026-11-14 01:00:00+00	2026-11-14 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.812498+00
6024	25	2026-11-16 01:00:00+00	2026-11-16 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.812498+00
6025	25	2026-11-16 06:30:00+00	2026-11-16 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.812498+00
6026	25	2026-11-17 01:00:00+00	2026-11-17 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.812498+00
6027	25	2026-11-17 06:30:00+00	2026-11-17 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.812498+00
6028	25	2026-11-18 01:00:00+00	2026-11-18 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.812498+00
6029	25	2026-11-18 06:30:00+00	2026-11-18 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.812498+00
6030	25	2026-11-19 01:00:00+00	2026-11-19 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.812498+00
6031	25	2026-11-19 06:30:00+00	2026-11-19 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.812498+00
6032	25	2026-11-20 01:00:00+00	2026-11-20 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.812498+00
6033	25	2026-11-20 06:30:00+00	2026-11-20 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.812498+00
6034	25	2026-11-21 01:00:00+00	2026-11-21 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.812498+00
6107	28	2026-11-07 01:00:00+00	2026-11-07 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.828553+00
6108	28	2026-11-07 06:30:00+00	2026-11-07 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.828553+00
6109	28	2026-11-09 01:00:00+00	2026-11-09 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.828553+00
6110	28	2026-11-09 06:30:00+00	2026-11-09 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.828553+00
6111	28	2026-11-10 01:00:00+00	2026-11-10 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.828553+00
6112	28	2026-11-10 06:30:00+00	2026-11-10 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.828553+00
6113	28	2026-11-11 01:00:00+00	2026-11-11 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.828553+00
6114	28	2026-11-11 06:30:00+00	2026-11-11 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.828553+00
6115	28	2026-11-12 01:00:00+00	2026-11-12 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.828553+00
6116	28	2026-11-12 06:30:00+00	2026-11-12 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.828553+00
2719	28	2026-10-31 01:00:00+00	2026-10-31 04:30:00+00	\N	t	ERP	2026-10-31 11:59:00.961217+00
2720	28	2026-10-31 06:30:00+00	2026-10-31 10:00:00+00	\N	t	ERP	2026-10-31 11:59:00.961217+00
6117	28	2026-11-13 01:00:00+00	2026-11-13 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.828553+00
6118	28	2026-11-13 06:30:00+00	2026-11-13 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.828553+00
6119	28	2026-11-14 01:00:00+00	2026-11-14 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.828553+00
6120	28	2026-11-14 06:30:00+00	2026-11-14 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.828553+00
6121	28	2026-11-16 01:00:00+00	2026-11-16 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.828553+00
6122	28	2026-11-16 06:30:00+00	2026-11-16 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.828553+00
6123	28	2026-11-17 01:00:00+00	2026-11-17 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.828553+00
6124	28	2026-11-17 06:30:00+00	2026-11-17 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.828553+00
6125	28	2026-11-18 01:00:00+00	2026-11-18 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.828553+00
6126	28	2026-11-18 06:30:00+00	2026-11-18 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.828553+00
6127	28	2026-11-19 01:00:00+00	2026-11-19 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.828553+00
6128	28	2026-11-19 06:30:00+00	2026-11-19 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.828553+00
6129	28	2026-11-20 01:00:00+00	2026-11-20 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.828553+00
6130	28	2026-11-20 06:30:00+00	2026-11-20 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.828553+00
6131	28	2026-11-21 01:00:00+00	2026-11-21 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.828553+00
6132	28	2026-11-21 06:30:00+00	2026-11-21 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.828553+00
5447	1	2026-11-07 01:00:00+00	2026-11-07 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.68875+00
5448	1	2026-11-09 01:00:00+00	2026-11-09 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.68875+00
5449	1	2026-11-09 06:30:00+00	2026-11-09 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.68875+00
5450	1	2026-11-10 01:00:00+00	2026-11-10 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.68875+00
5451	1	2026-11-10 06:30:00+00	2026-11-10 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.68875+00
5452	1	2026-11-11 01:00:00+00	2026-11-11 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.68875+00
5453	1	2026-11-11 06:30:00+00	2026-11-11 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.68875+00
5454	1	2026-11-12 01:00:00+00	2026-11-12 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.68875+00
5455	1	2026-11-12 06:30:00+00	2026-11-12 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.68875+00
5456	1	2026-11-13 01:00:00+00	2026-11-13 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.68875+00
5457	1	2026-11-13 06:30:00+00	2026-11-13 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.68875+00
5458	1	2026-11-14 01:00:00+00	2026-11-14 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.68875+00
5459	1	2026-11-16 01:00:00+00	2026-11-16 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.68875+00
5460	1	2026-11-16 06:30:00+00	2026-11-16 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.68875+00
5461	1	2026-11-17 01:00:00+00	2026-11-17 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.68875+00
5462	1	2026-11-17 06:30:00+00	2026-11-17 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.68875+00
5463	1	2026-11-18 01:00:00+00	2026-11-18 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.68875+00
5464	1	2026-11-18 06:30:00+00	2026-11-18 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.68875+00
5465	1	2026-11-19 01:00:00+00	2026-11-19 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.68875+00
5466	1	2026-11-19 06:30:00+00	2026-11-19 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.68875+00
5467	1	2026-11-20 01:00:00+00	2026-11-20 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.68875+00
5468	1	2026-11-20 06:30:00+00	2026-11-20 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.68875+00
5469	1	2026-11-21 01:00:00+00	2026-11-21 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.68875+00
5545	5	2026-11-07 01:00:00+00	2026-11-07 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.720657+00
5546	5	2026-11-09 01:00:00+00	2026-11-09 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.720657+00
5547	5	2026-11-09 06:30:00+00	2026-11-09 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.720657+00
5548	5	2026-11-10 01:00:00+00	2026-11-10 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.720657+00
5549	5	2026-11-10 06:30:00+00	2026-11-10 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.720657+00
5550	5	2026-11-11 01:00:00+00	2026-11-11 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.720657+00
5551	5	2026-11-11 06:30:00+00	2026-11-11 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.720657+00
5552	5	2026-11-12 01:00:00+00	2026-11-12 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.720657+00
5553	5	2026-11-12 06:30:00+00	2026-11-12 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.720657+00
5554	5	2026-11-13 01:00:00+00	2026-11-13 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.720657+00
5555	5	2026-11-13 06:30:00+00	2026-11-13 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.720657+00
5556	5	2026-11-14 01:00:00+00	2026-11-14 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.720657+00
5557	5	2026-11-16 01:00:00+00	2026-11-16 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.720657+00
5558	5	2026-11-16 06:30:00+00	2026-11-16 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.720657+00
5559	5	2026-11-17 01:00:00+00	2026-11-17 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.720657+00
5560	5	2026-11-17 06:30:00+00	2026-11-17 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.720657+00
5561	5	2026-11-18 01:00:00+00	2026-11-18 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.720657+00
5562	5	2026-11-18 06:30:00+00	2026-11-18 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.720657+00
5563	5	2026-11-19 01:00:00+00	2026-11-19 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.720657+00
5564	5	2026-11-19 06:30:00+00	2026-11-19 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.720657+00
5565	5	2026-11-20 01:00:00+00	2026-11-20 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.720657+00
5566	5	2026-11-20 06:30:00+00	2026-11-20 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.720657+00
5567	5	2026-11-21 01:00:00+00	2026-11-21 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.720657+00
5643	9	2026-11-07 01:00:00+00	2026-11-07 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.743628+00
5644	9	2026-11-09 01:00:00+00	2026-11-09 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.743628+00
5645	9	2026-11-09 06:30:00+00	2026-11-09 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.743628+00
5646	9	2026-11-10 01:00:00+00	2026-11-10 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.743628+00
5647	9	2026-11-10 06:30:00+00	2026-11-10 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.743628+00
5648	9	2026-11-11 01:00:00+00	2026-11-11 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.743628+00
5649	9	2026-11-11 06:30:00+00	2026-11-11 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.743628+00
5650	9	2026-11-12 01:00:00+00	2026-11-12 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.743628+00
5651	9	2026-11-12 06:30:00+00	2026-11-12 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.743628+00
5652	9	2026-11-13 01:00:00+00	2026-11-13 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.743628+00
5653	9	2026-11-13 06:30:00+00	2026-11-13 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.743628+00
5654	9	2026-11-14 01:00:00+00	2026-11-14 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.743628+00
5655	9	2026-11-16 01:00:00+00	2026-11-16 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.743628+00
5656	9	2026-11-16 06:30:00+00	2026-11-16 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.743628+00
5657	9	2026-11-17 01:00:00+00	2026-11-17 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.743628+00
5658	9	2026-11-17 06:30:00+00	2026-11-17 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.743628+00
5659	9	2026-11-18 01:00:00+00	2026-11-18 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.743628+00
5660	9	2026-11-18 06:30:00+00	2026-11-18 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.743628+00
5661	9	2026-11-19 01:00:00+00	2026-11-19 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.743628+00
5662	9	2026-11-19 06:30:00+00	2026-11-19 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.743628+00
5663	9	2026-11-20 01:00:00+00	2026-11-20 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.743628+00
5664	9	2026-11-20 06:30:00+00	2026-11-20 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.743628+00
5665	9	2026-11-21 01:00:00+00	2026-11-21 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.743628+00
5741	13	2026-11-07 01:00:00+00	2026-11-07 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.764151+00
5742	13	2026-11-09 01:00:00+00	2026-11-09 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.764151+00
5743	13	2026-11-09 06:30:00+00	2026-11-09 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.764151+00
5744	13	2026-11-10 01:00:00+00	2026-11-10 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.764151+00
5745	13	2026-11-10 06:30:00+00	2026-11-10 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.764151+00
5746	13	2026-11-11 01:00:00+00	2026-11-11 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.764151+00
5747	13	2026-11-11 06:30:00+00	2026-11-11 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.764151+00
5748	13	2026-11-12 01:00:00+00	2026-11-12 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.764151+00
5749	13	2026-11-12 06:30:00+00	2026-11-12 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.764151+00
5750	13	2026-11-13 01:00:00+00	2026-11-13 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.764151+00
5751	13	2026-11-13 06:30:00+00	2026-11-13 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.764151+00
5752	13	2026-11-14 01:00:00+00	2026-11-14 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.764151+00
5753	13	2026-11-16 01:00:00+00	2026-11-16 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.764151+00
5754	13	2026-11-16 06:30:00+00	2026-11-16 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.764151+00
5755	13	2026-11-17 01:00:00+00	2026-11-17 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.764151+00
5756	13	2026-11-17 06:30:00+00	2026-11-17 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.764151+00
5757	13	2026-11-18 01:00:00+00	2026-11-18 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.764151+00
5758	13	2026-11-18 06:30:00+00	2026-11-18 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.764151+00
5759	13	2026-11-19 01:00:00+00	2026-11-19 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.764151+00
5760	13	2026-11-19 06:30:00+00	2026-11-19 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.764151+00
5761	13	2026-11-20 01:00:00+00	2026-11-20 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.764151+00
5762	13	2026-11-20 06:30:00+00	2026-11-20 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.764151+00
5763	13	2026-11-21 01:00:00+00	2026-11-21 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.764151+00
5839	17	2026-11-07 01:00:00+00	2026-11-07 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.782797+00
5840	17	2026-11-09 01:00:00+00	2026-11-09 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.782797+00
5841	17	2026-11-09 06:30:00+00	2026-11-09 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.782797+00
5842	17	2026-11-10 01:00:00+00	2026-11-10 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.782797+00
5843	17	2026-11-10 06:30:00+00	2026-11-10 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.782797+00
5470	2	2026-11-07 01:00:00+00	2026-11-07 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.70006+00
5471	2	2026-11-07 06:30:00+00	2026-11-07 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.70006+00
5472	2	2026-11-09 01:00:00+00	2026-11-09 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.70006+00
5473	2	2026-11-09 06:30:00+00	2026-11-09 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.70006+00
5474	2	2026-11-10 01:00:00+00	2026-11-10 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.70006+00
5475	2	2026-11-10 06:30:00+00	2026-11-10 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.70006+00
5476	2	2026-11-11 01:00:00+00	2026-11-11 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.70006+00
5477	2	2026-11-11 06:30:00+00	2026-11-11 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.70006+00
5478	2	2026-11-12 01:00:00+00	2026-11-12 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.70006+00
5479	2	2026-11-12 06:30:00+00	2026-11-12 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.70006+00
5480	2	2026-11-13 01:00:00+00	2026-11-13 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.70006+00
5481	2	2026-11-13 06:30:00+00	2026-11-13 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.70006+00
5482	2	2026-11-14 01:00:00+00	2026-11-14 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.70006+00
5483	2	2026-11-14 06:30:00+00	2026-11-14 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.70006+00
5484	2	2026-11-16 01:00:00+00	2026-11-16 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.70006+00
5485	2	2026-11-16 06:30:00+00	2026-11-16 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.70006+00
5486	2	2026-11-17 01:00:00+00	2026-11-17 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.70006+00
5487	2	2026-11-17 06:30:00+00	2026-11-17 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.70006+00
5488	2	2026-11-18 01:00:00+00	2026-11-18 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.70006+00
5489	2	2026-11-18 06:30:00+00	2026-11-18 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.70006+00
5490	2	2026-11-19 01:00:00+00	2026-11-19 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.70006+00
5491	2	2026-11-19 06:30:00+00	2026-11-19 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.70006+00
5492	2	2026-11-20 01:00:00+00	2026-11-20 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.70006+00
5493	2	2026-11-20 06:30:00+00	2026-11-20 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.70006+00
5494	2	2026-11-21 01:00:00+00	2026-11-21 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.70006+00
5495	2	2026-11-21 06:30:00+00	2026-11-21 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.70006+00
5568	6	2026-11-07 01:00:00+00	2026-11-07 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.726211+00
5569	6	2026-11-07 06:30:00+00	2026-11-07 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.726211+00
5570	6	2026-11-09 01:00:00+00	2026-11-09 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.726211+00
5571	6	2026-11-09 06:30:00+00	2026-11-09 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.726211+00
5572	6	2026-11-10 01:00:00+00	2026-11-10 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.726211+00
5573	6	2026-11-10 06:30:00+00	2026-11-10 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.726211+00
5574	6	2026-11-11 01:00:00+00	2026-11-11 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.726211+00
5575	6	2026-11-11 06:30:00+00	2026-11-11 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.726211+00
5576	6	2026-11-12 01:00:00+00	2026-11-12 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.726211+00
5577	6	2026-11-12 06:30:00+00	2026-11-12 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.726211+00
5578	6	2026-11-13 01:00:00+00	2026-11-13 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.726211+00
5579	6	2026-11-13 06:30:00+00	2026-11-13 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.726211+00
5580	6	2026-11-14 01:00:00+00	2026-11-14 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.726211+00
5581	6	2026-11-14 06:30:00+00	2026-11-14 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.726211+00
5582	6	2026-11-16 01:00:00+00	2026-11-16 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.726211+00
5583	6	2026-11-16 06:30:00+00	2026-11-16 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.726211+00
5584	6	2026-11-17 01:00:00+00	2026-11-17 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.726211+00
5585	6	2026-11-17 06:30:00+00	2026-11-17 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.726211+00
5586	6	2026-11-18 01:00:00+00	2026-11-18 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.726211+00
5587	6	2026-11-18 06:30:00+00	2026-11-18 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.726211+00
5588	6	2026-11-19 01:00:00+00	2026-11-19 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.726211+00
5589	6	2026-11-19 06:30:00+00	2026-11-19 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.726211+00
5590	6	2026-11-20 01:00:00+00	2026-11-20 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.726211+00
5591	6	2026-11-20 06:30:00+00	2026-11-20 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.726211+00
5592	6	2026-11-21 01:00:00+00	2026-11-21 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.726211+00
5593	6	2026-11-21 06:30:00+00	2026-11-21 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.726211+00
5666	10	2026-11-07 01:00:00+00	2026-11-07 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.748725+00
5667	10	2026-11-07 06:30:00+00	2026-11-07 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.748725+00
5668	10	2026-11-09 01:00:00+00	2026-11-09 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.748725+00
5669	10	2026-11-09 06:30:00+00	2026-11-09 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.748725+00
5670	10	2026-11-10 01:00:00+00	2026-11-10 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.748725+00
5671	10	2026-11-10 06:30:00+00	2026-11-10 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.748725+00
5672	10	2026-11-11 01:00:00+00	2026-11-11 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.748725+00
5673	10	2026-11-11 06:30:00+00	2026-11-11 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.748725+00
5674	10	2026-11-12 01:00:00+00	2026-11-12 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.748725+00
5675	10	2026-11-12 06:30:00+00	2026-11-12 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.748725+00
5676	10	2026-11-13 01:00:00+00	2026-11-13 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.748725+00
5677	10	2026-11-13 06:30:00+00	2026-11-13 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.748725+00
5678	10	2026-11-14 01:00:00+00	2026-11-14 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.748725+00
5679	10	2026-11-14 06:30:00+00	2026-11-14 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.748725+00
5680	10	2026-11-16 01:00:00+00	2026-11-16 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.748725+00
5681	10	2026-11-16 06:30:00+00	2026-11-16 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.748725+00
5682	10	2026-11-17 01:00:00+00	2026-11-17 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.748725+00
5683	10	2026-11-17 06:30:00+00	2026-11-17 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.748725+00
5684	10	2026-11-18 01:00:00+00	2026-11-18 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.748725+00
5685	10	2026-11-18 06:30:00+00	2026-11-18 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.748725+00
5686	10	2026-11-19 01:00:00+00	2026-11-19 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.748725+00
5687	10	2026-11-19 06:30:00+00	2026-11-19 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.748725+00
5688	10	2026-11-20 01:00:00+00	2026-11-20 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.748725+00
5689	10	2026-11-20 06:30:00+00	2026-11-20 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.748725+00
5690	10	2026-11-21 01:00:00+00	2026-11-21 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.748725+00
5691	10	2026-11-21 06:30:00+00	2026-11-21 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.748725+00
5764	14	2026-11-07 01:00:00+00	2026-11-07 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.768675+00
5765	14	2026-11-07 06:30:00+00	2026-11-07 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.768675+00
5766	14	2026-11-09 01:00:00+00	2026-11-09 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.768675+00
5767	14	2026-11-09 06:30:00+00	2026-11-09 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.768675+00
5768	14	2026-11-10 01:00:00+00	2026-11-10 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.768675+00
5769	14	2026-11-10 06:30:00+00	2026-11-10 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.768675+00
5770	14	2026-11-11 01:00:00+00	2026-11-11 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.768675+00
5771	14	2026-11-11 06:30:00+00	2026-11-11 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.768675+00
5772	14	2026-11-12 01:00:00+00	2026-11-12 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.768675+00
5773	14	2026-11-12 06:30:00+00	2026-11-12 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.768675+00
5774	14	2026-11-13 01:00:00+00	2026-11-13 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.768675+00
5775	14	2026-11-13 06:30:00+00	2026-11-13 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.768675+00
5776	14	2026-11-14 01:00:00+00	2026-11-14 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.768675+00
5777	14	2026-11-14 06:30:00+00	2026-11-14 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.768675+00
5778	14	2026-11-16 01:00:00+00	2026-11-16 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.768675+00
5779	14	2026-11-16 06:30:00+00	2026-11-16 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.768675+00
5780	14	2026-11-17 01:00:00+00	2026-11-17 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.768675+00
5781	14	2026-11-17 06:30:00+00	2026-11-17 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.768675+00
5782	14	2026-11-18 01:00:00+00	2026-11-18 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.768675+00
5783	14	2026-11-18 06:30:00+00	2026-11-18 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.768675+00
5784	14	2026-11-19 01:00:00+00	2026-11-19 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.768675+00
5785	14	2026-11-19 06:30:00+00	2026-11-19 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.768675+00
5786	14	2026-11-20 01:00:00+00	2026-11-20 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.768675+00
5787	14	2026-11-20 06:30:00+00	2026-11-20 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.768675+00
5788	14	2026-11-21 01:00:00+00	2026-11-21 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.768675+00
5789	14	2026-11-21 06:30:00+00	2026-11-21 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.768675+00
5862	18	2026-11-07 01:00:00+00	2026-11-07 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.786698+00
5863	18	2026-11-07 06:30:00+00	2026-11-07 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.786698+00
5864	18	2026-11-09 01:00:00+00	2026-11-09 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.786698+00
5865	18	2026-11-09 06:30:00+00	2026-11-09 10:00:00+00	\N	t	ERP	2026-11-07 01:53:06.786698+00
5866	18	2026-11-10 01:00:00+00	2026-11-10 04:30:00+00	\N	t	ERP	2026-11-07 01:53:06.786698+00
\.


--
-- Data for Name: doctors; Type: TABLE DATA; Schema: public; Owner: healthcare
--

COPY public.doctors (id, hospital_id, department_id, full_name, title, qualifications, experience_years, introduction, consultation_fee, avatar_url, erp_doctor_id, rating_avg, rating_count, is_active, created_at, updated_at) FROM stdin;
1	1	1	Dr. Tran Lan Anh	MD	Doctor of Medicine; specialist training in General Internal Medicine.	12	Fictional general internal medicine specialist at Riverside General Hospital, focused on clear explanations and shared decisions.	250000.00	\N	ERP-D0001	0.00	0	t	2026-10-31 11:28:57.838863+00	2026-10-31 11:28:57.838865+00
2	1	1	Dr. Le Thanh Tung	MD	Doctor of Medicine; specialist training in General Internal Medicine.	19	Fictional general internal medicine specialist at Riverside General Hospital, focused on clear explanations and shared decisions.	300000.00	\N	ERP-D0002	0.00	0	t	2026-10-31 11:28:57.838865+00	2026-10-31 11:28:57.838866+00
3	1	2	Dr. Pham Hai Yen	MD, PhD	Doctor of Medicine; specialist training in Respiratory Medicine.	6	Fictional respiratory medicine specialist at Riverside General Hospital, focused on clear explanations and shared decisions.	350000.00	\N	ERP-D0003	0.00	0	t	2026-10-31 11:28:57.843969+00	2026-10-31 11:28:57.843973+00
4	1	2	Dr. Hoang Quoc Bao	MD	Doctor of Medicine; specialist training in Respiratory Medicine.	13	Fictional respiratory medicine specialist at Riverside General Hospital, focused on clear explanations and shared decisions.	200000.00	\N	ERP-D0004	0.00	0	t	2026-10-31 11:28:57.843973+00	2026-10-31 11:28:57.843974+00
5	1	3	Dr. Vo Ngoc Mai	MD	Doctor of Medicine; specialist training in Cardiology.	20	Fictional cardiology specialist at Riverside General Hospital, focused on clear explanations and shared decisions.	250000.00	\N	ERP-D0005	0.00	0	t	2026-10-31 11:28:57.846546+00	2026-10-31 11:28:57.846547+00
6	1	3	Dr. Dang Gia Khanh	MD, PhD	Doctor of Medicine; specialist training in Cardiology.	7	Fictional cardiology specialist at Riverside General Hospital, focused on clear explanations and shared decisions.	300000.00	\N	ERP-D0006	0.00	0	t	2026-10-31 11:28:57.846547+00	2026-10-31 11:28:57.846548+00
7	1	4	Dr. Bui Thu Ha	MD	Doctor of Medicine; specialist training in Gastroenterology.	14	Fictional gastroenterology specialist at Riverside General Hospital, focused on clear explanations and shared decisions.	350000.00	\N	ERP-D0007	0.00	0	t	2026-10-31 11:28:57.848613+00	2026-10-31 11:28:57.848616+00
8	1	4	Dr. Nguyen Duc Huy	MD	Doctor of Medicine; specialist training in Gastroenterology.	21	Fictional gastroenterology specialist at Riverside General Hospital, focused on clear explanations and shared decisions.	200000.00	\N	ERP-D0008	0.00	0	t	2026-10-31 11:28:57.848617+00	2026-10-31 11:28:57.848617+00
9	1	5	Dr. Tran Bich Ngoc	MD, PhD	Doctor of Medicine; specialist training in Neurology.	8	Fictional neurology specialist at Riverside General Hospital, focused on clear explanations and shared decisions.	250000.00	\N	ERP-D0009	0.00	0	t	2026-10-31 11:28:57.849983+00	2026-10-31 11:28:57.849985+00
10	1	5	Dr. Le Minh An	MD	Doctor of Medicine; specialist training in Neurology.	15	Fictional neurology specialist at Riverside General Hospital, focused on clear explanations and shared decisions.	300000.00	\N	ERP-D0010	0.00	0	t	2026-10-31 11:28:57.849985+00	2026-10-31 11:28:57.849986+00
11	1	6	Dr. Pham Lan Anh	MD	Doctor of Medicine; specialist training in Orthopedics.	22	Fictional orthopedics specialist at Riverside General Hospital, focused on clear explanations and shared decisions.	350000.00	\N	ERP-D0011	0.00	0	t	2026-10-31 11:28:57.851276+00	2026-10-31 11:28:57.851278+00
12	1	6	Dr. Hoang Thanh Tung	MD, PhD	Doctor of Medicine; specialist training in Orthopedics.	9	Fictional orthopedics specialist at Riverside General Hospital, focused on clear explanations and shared decisions.	200000.00	\N	ERP-D0012	0.00	0	t	2026-10-31 11:28:57.851279+00	2026-10-31 11:28:57.851279+00
13	2	7	Dr. Vo Hai Yen	MD	Doctor of Medicine; specialist training in Dermatology.	16	Fictional dermatology specialist at Lotus Skin & Eye Clinic, focused on clear explanations and shared decisions.	250000.00	\N	ERP-D0013	0.00	0	t	2026-10-31 11:28:57.853389+00	2026-10-31 11:28:57.85339+00
14	2	7	Dr. Dang Quoc Bao	MD	Doctor of Medicine; specialist training in Dermatology.	23	Fictional dermatology specialist at Lotus Skin & Eye Clinic, focused on clear explanations and shared decisions.	300000.00	\N	ERP-D0014	0.00	0	t	2026-10-31 11:28:57.853391+00	2026-10-31 11:28:57.853391+00
15	2	8	Dr. Bui Ngoc Mai	MD, PhD	Doctor of Medicine; specialist training in Ophthalmology.	10	Fictional ophthalmology specialist at Lotus Skin & Eye Clinic, focused on clear explanations and shared decisions.	350000.00	\N	ERP-D0015	0.00	0	t	2026-10-31 11:28:57.854942+00	2026-10-31 11:28:57.854943+00
16	2	8	Dr. Nguyen Gia Khanh	MD	Doctor of Medicine; specialist training in Ophthalmology.	17	Fictional ophthalmology specialist at Lotus Skin & Eye Clinic, focused on clear explanations and shared decisions.	200000.00	\N	ERP-D0016	0.00	0	t	2026-10-31 11:28:57.854943+00	2026-10-31 11:28:57.854944+00
17	3	9	Dr. Tran Thu Ha	MD	Doctor of Medicine; specialist training in General Internal Medicine.	24	Fictional general internal medicine specialist at Green Valley Medical Center, focused on clear explanations and shared decisions.	250000.00	\N	ERP-D0017	0.00	0	t	2026-10-31 11:28:57.856676+00	2026-10-31 11:28:57.856677+00
18	3	9	Dr. Le Duc Huy	MD, PhD	Doctor of Medicine; specialist training in General Internal Medicine.	11	Fictional general internal medicine specialist at Green Valley Medical Center, focused on clear explanations and shared decisions.	300000.00	\N	ERP-D0018	0.00	0	t	2026-10-31 11:28:57.856678+00	2026-10-31 11:28:57.856679+00
19	3	10	Dr. Pham Bich Ngoc	MD	Doctor of Medicine; specialist training in Pediatrics.	18	Fictional pediatrics specialist at Green Valley Medical Center, focused on clear explanations and shared decisions.	350000.00	\N	ERP-D0019	0.00	0	t	2026-10-31 11:28:57.857782+00	2026-10-31 11:28:57.857783+00
20	3	10	Dr. Hoang Minh An	MD	Doctor of Medicine; specialist training in Pediatrics.	5	Fictional pediatrics specialist at Green Valley Medical Center, focused on clear explanations and shared decisions.	200000.00	\N	ERP-D0020	0.00	0	t	2026-10-31 11:28:57.857784+00	2026-10-31 11:28:57.857784+00
21	3	11	Dr. Vo Lan Anh	MD, PhD	Doctor of Medicine; specialist training in Otorhinolaryngology (ENT).	12	Fictional otorhinolaryngology (ent) specialist at Green Valley Medical Center, focused on clear explanations and shared decisions.	250000.00	\N	ERP-D0021	0.00	0	t	2026-10-31 11:28:57.859369+00	2026-10-31 11:28:57.85937+00
22	3	11	Dr. Dang Thanh Tung	MD	Doctor of Medicine; specialist training in Otorhinolaryngology (ENT).	19	Fictional otorhinolaryngology (ent) specialist at Green Valley Medical Center, focused on clear explanations and shared decisions.	300000.00	\N	ERP-D0022	0.00	0	t	2026-10-31 11:28:57.859371+00	2026-10-31 11:28:57.859371+00
24	3	12	Dr. Nguyen Quoc Bao	MD, PhD	Doctor of Medicine; specialist training in Rheumatology.	13	Fictional rheumatology specialist at Green Valley Medical Center, focused on clear explanations and shared decisions.	200000.00	\N	ERP-D0024	0.00	0	t	2026-10-31 11:28:57.860432+00	2026-10-31 11:28:57.860432+00
25	3	13	Dr. Tran Ngoc Mai	MD	Doctor of Medicine; specialist training in Orthopedics.	20	Fictional orthopedics specialist at Green Valley Medical Center, focused on clear explanations and shared decisions.	250000.00	\N	ERP-D0025	0.00	0	t	2026-10-31 11:28:57.862108+00	2026-10-31 11:28:57.862109+00
26	3	13	Dr. Le Gia Khanh	MD	Doctor of Medicine; specialist training in Orthopedics.	7	Fictional orthopedics specialist at Green Valley Medical Center, focused on clear explanations and shared decisions.	300000.00	\N	ERP-D0026	0.00	0	t	2026-10-31 11:28:57.86211+00	2026-10-31 11:28:57.86211+00
23	3	12	Dr. Bui Hai Yen	MD	Doctor of Medicine; specialist training in Rheumatology.	6	Fictional rheumatology specialist at Green Valley Medical Center, focused on clear explanations and shared decisions.	350000.00	\N	ERP-D0023	5.00	1	t	2026-10-31 11:28:57.86043+00	2026-11-07 01:48:30.235673+00
27	3	14	Dr. Pham Thu Ha	MD, PhD	Doctor of Medicine; specialist training in Respiratory Medicine.	14	Fictional respiratory medicine specialist at Green Valley Medical Center, focused on clear explanations and shared decisions.	350000.00	\N	ERP-D0027	0.00	0	t	2026-10-31 11:28:57.862833+00	2026-10-31 11:28:57.862834+00
28	3	14	Dr. Hoang Duc Huy	MD	Doctor of Medicine; specialist training in Respiratory Medicine.	21	Fictional respiratory medicine specialist at Green Valley Medical Center, focused on clear explanations and shared decisions.	200000.00	\N	ERP-D0028	0.00	0	t	2026-10-31 11:28:57.862835+00	2026-10-31 11:28:57.862835+00
\.


--
-- Data for Name: hospitals; Type: TABLE DATA; Schema: public; Owner: healthcare
--

COPY public.hospitals (id, name, facility_type, address, city, phone, email, website, description, is_active, created_at, updated_at) FROM stdin;
1	Riverside General Hospital	HOSPITAL	12 Riverside Avenue, District 1	Ho Chi Minh City	+842800000001	contact@riverside-general.example	\N	Fictional multi-specialty hospital used for demonstration.	t	2026-10-31 11:28:57.833548+00	2026-10-31 11:28:57.83355+00
2	Lotus Skin & Eye Clinic	CLINIC	88 Lotus Street, District 3	Ho Chi Minh City	+842800000002	hello@lotus-clinic.example	\N	Fictional outpatient clinic for dermatology and ophthalmology.	t	2026-10-31 11:28:57.850868+00	2026-10-31 11:28:57.85087+00
3	Green Valley Medical Center	HOSPITAL	5 Green Valley Road, Cau Giay	Hanoi	+842400000003	info@greenvalley-medical.example	\N	Fictional regional medical center.	t	2026-10-31 11:28:57.854421+00	2026-10-31 11:28:57.854427+00
4	Smoke Clinic	CLINIC	9 Test Rd	Da Nang	\N	\N	\N	\N	f	2026-11-07 01:48:30.24581+00	2026-11-07 01:48:30.260142+00
\.


--
-- Data for Name: notifications; Type: TABLE DATA; Schema: public; Owner: healthcare
--

COPY public.notifications (id, user_id, type, title, content, link, created_at, read_at) FROM stdin;
1	3	BOOKING_SUBMITTED	Booking request submitted	Your booking request HKHE8BY2E3 for 02/11/2026 13:30 has been submitted and is awaiting confirmation.	/appointments/2	2026-10-31 11:35:01.516824+00	\N
2	3	APPOINTMENT_STATUS	Appointment confirmed	Your appointment HKHE8BY2E3 on 02/11/2026 13:30 has been confirmed by the hospital.	/appointments/2	2026-10-31 11:35:01.604941+00	\N
3	3	PAYMENT_RESULT	Payment successful	We received your payment for appointment HKHE8BY2E3.	/appointments/2	2026-10-31 11:35:02.239677+00	\N
4	3	APPOINTMENT_STATUS	Appointment cancelled	Your appointment HKHE8BY2E3 on 02/11/2026 13:30 has been cancelled. Reason: Plans changed	/appointments/2	2026-10-31 11:35:03.351707+00	\N
5	3	PAYMENT_RESULT	Refund issued	Your payment for appointment HKHE8BY2E3 has been refunded.	/appointments/2	2026-10-31 11:35:03.358701+00	\N
6	4	BOOKING_SUBMITTED	Booking request submitted	Your booking request HKA9HX3RHX for 02/11/2026 13:30 has been submitted and is awaiting confirmation.	/appointments/3	2026-10-31 11:40:47.85234+00	\N
7	4	APPOINTMENT_STATUS	Appointment confirmed	Your appointment HKA9HX3RHX on 02/11/2026 13:30 has been confirmed by the hospital.	/appointments/3	2026-10-31 11:40:47.932503+00	\N
8	4	PAYMENT_RESULT	Payment successful	We received your payment for appointment HKA9HX3RHX.	/appointments/3	2026-10-31 11:40:48.569822+00	\N
9	4	APPOINTMENT_STATUS	Appointment cancelled	Your appointment HKA9HX3RHX on 02/11/2026 13:30 has been cancelled. Reason: Plans changed	/appointments/3	2026-10-31 11:40:49.703977+00	\N
10	4	PAYMENT_RESULT	Refund issued	Your payment for appointment HKA9HX3RHX has been refunded.	/appointments/3	2026-10-31 11:40:49.710837+00	\N
11	5	BOOKING_SUBMITTED	Booking request submitted	Your booking request HKLLYS9XU7 for 02/11/2026 13:30 has been submitted and is awaiting confirmation.	/appointments/4	2026-10-31 11:42:09.69806+00	\N
12	5	APPOINTMENT_STATUS	Appointment confirmed	Your appointment HKLLYS9XU7 on 02/11/2026 13:30 has been confirmed by the hospital.	/appointments/4	2026-10-31 11:42:09.762463+00	\N
13	5	PAYMENT_RESULT	Payment successful	We received your payment for appointment HKLLYS9XU7.	/appointments/4	2026-10-31 11:42:10.35409+00	\N
14	5	APPOINTMENT_STATUS	Appointment cancelled	Your appointment HKLLYS9XU7 on 02/11/2026 13:30 has been cancelled. Reason: Plans changed	/appointments/4	2026-10-31 11:42:11.493919+00	\N
15	5	PAYMENT_RESULT	Refund issued	Your payment for appointment HKLLYS9XU7 has been refunded.	/appointments/4	2026-10-31 11:42:11.501075+00	\N
16	6	BOOKING_SUBMITTED	Booking request submitted	Your booking request HKCGJVQ3CG for 02/11/2026 13:30 has been submitted and is awaiting confirmation.	/appointments/5	2026-10-31 12:02:20.360648+00	\N
17	6	APPOINTMENT_STATUS	Appointment confirmed	Your appointment HKCGJVQ3CG on 02/11/2026 13:30 has been confirmed by the hospital.	/appointments/5	2026-10-31 12:02:20.421493+00	\N
18	6	PAYMENT_RESULT	Payment successful	We received your payment for appointment HKCGJVQ3CG.	/appointments/5	2026-10-31 12:02:21.024626+00	\N
19	6	APPOINTMENT_STATUS	Appointment cancelled	Your appointment HKCGJVQ3CG on 02/11/2026 13:30 has been cancelled. Reason: Plans changed	/appointments/5	2026-10-31 12:02:22.109943+00	\N
20	6	PAYMENT_RESULT	Refund issued	Your payment for appointment HKCGJVQ3CG has been refunded.	/appointments/5	2026-10-31 12:02:22.115214+00	\N
21	2	BOOKING_SUBMITTED	Booking request submitted	Your booking request HKBF3GEYSJ for 09/11/2026 13:30 has been submitted and is awaiting confirmation.	/appointments/6	2026-11-07 01:48:29.351476+00	2026-11-07 01:48:30.081568+00
22	2	APPOINTMENT_STATUS	Appointment confirmed	Your appointment HKBF3GEYSJ on 09/11/2026 13:30 has been confirmed by the hospital.	/appointments/6	2026-11-07 01:48:29.41692+00	2026-11-07 01:48:30.081568+00
23	2	PAYMENT_RESULT	Payment successful	We received your payment for appointment HKBF3GEYSJ.	/appointments/6	2026-11-07 01:48:29.56739+00	2026-11-07 01:48:30.081568+00
24	2	CHECK_IN	Checked in	The hospital has recorded your arrival for appointment HKBF3GEYSJ.	/appointments/6	2026-11-07 01:48:29.651867+00	2026-11-07 01:48:30.081568+00
25	2	APPOINTMENT_STATUS	Appointment completed	Your appointment HKBF3GEYSJ has been completed. You can now review your doctor.	/appointments/6	2026-11-07 01:48:29.688053+00	2026-11-07 01:48:30.081568+00
26	2	BOOKING_SUBMITTED	Booking request submitted	Your booking request HK46HZ3CDG for 10/11/2026 13:30 has been submitted and is awaiting confirmation.	/appointments/7	2026-11-07 01:48:29.762492+00	2026-11-07 01:48:30.081568+00
27	2	APPOINTMENT_STATUS	Appointment confirmed	Your appointment HK46HZ3CDG on 10/11/2026 13:30 has been confirmed by the hospital.	/appointments/7	2026-11-07 01:48:29.817878+00	2026-11-07 01:48:30.081568+00
28	2	PAYMENT_RESULT	Payment successful	We received your payment for appointment HK46HZ3CDG.	/appointments/7	2026-11-07 01:48:29.869616+00	2026-11-07 01:48:30.081568+00
29	2	APPOINTMENT_STATUS	Appointment cancelled	Your appointment HK46HZ3CDG on 10/11/2026 13:30 has been cancelled. Reason: Smoke test	/appointments/7	2026-11-07 01:48:29.893245+00	2026-11-07 01:48:30.081568+00
30	2	PAYMENT_RESULT	Refund issued	Your payment for appointment HK46HZ3CDG has been refunded.	/appointments/7	2026-11-07 01:48:29.898301+00	2026-11-07 01:48:30.081568+00
31	2	BOOKING_SUBMITTED	Booking request submitted	Your booking request HKLJN84UF7 for 11/11/2026 13:30 has been submitted and is awaiting confirmation.	/appointments/8	2026-11-07 01:48:29.94965+00	2026-11-07 01:48:30.081568+00
32	2	APPOINTMENT_STATUS	Appointment confirmed	Your appointment HKLJN84UF7 on 11/11/2026 13:30 has been confirmed by the hospital.	/appointments/8	2026-11-07 01:48:30.005546+00	2026-11-07 01:48:30.081568+00
33	2	PAYMENT_RESULT	Payment failed	Your payment for appointment HKLJN84UF7 did not go through. You can try again from the appointment page.	/appointments/8	2026-11-07 01:48:30.050121+00	2026-11-07 01:48:30.081568+00
\.


--
-- Data for Name: patient_profiles; Type: TABLE DATA; Schema: public; Owner: healthcare
--

COPY public.patient_profiles (id, user_id, full_name, date_of_birth, phone_number, address, created_at, updated_at) FROM stdin;
1	2	Demo Patient	1995-05-20	+84901234567	\N	2026-10-31 11:28:58.027941+00	2026-10-31 11:28:58.027942+00
2	3	E2E Patient	1992-04-15	+84912000111	\N	2026-10-31 11:34:59.911231+00	2026-10-31 11:34:59.911233+00
3	4	E2E Patient	1992-04-15	+84912000111	\N	2026-10-31 11:40:46.392605+00	2026-10-31 11:40:46.392606+00
4	5	E2E Patient	1992-04-15	+84912000111	\N	2026-10-31 11:42:08.22031+00	2026-10-31 11:42:08.220313+00
5	6	E2E Patient	1992-04-15	+84912000111	\N	2026-10-31 12:02:18.897327+00	2026-10-31 12:02:18.897329+00
6	7	Smoke Tester	1990-02-03	+84912345678	1 Test Street	2026-11-07 01:48:29.207144+00	2026-11-07 01:48:29.235825+00
7	8	Hoang Nguyen	2005-06-13	0967318521	61	2026-11-07 01:49:48.09761+00	2026-11-07 01:49:58.416916+00
\.


--
-- Data for Name: payments; Type: TABLE DATA; Schema: public; Owner: healthcare
--

COPY public.payments (id, appointment_id, amount, currency, status, provider, provider_reference, checkout_url, failure_reason, last_event_id, paid_at, refunded_at, created_at, updated_at) FROM stdin;
1	2	150000.00	VND	REFUNDED	mock	MP-B510056446E2	http://localhost:8080/mock-payment/checkout/MP-B510056446E2	\N	e0841edef62948db99f3f2c53cb5af5c	2026-10-31 11:35:02.198851+00	2026-10-31 11:35:03.355312+00	2026-10-31 11:35:02.064757+00	2026-10-31 11:35:03.357177+00
2	3	150000.00	VND	REFUNDED	mock	MP-017E70F22B4F	http://localhost:8080/mock-payment/checkout/MP-017E70F22B4F	\N	a1c4c59535904eb884bc17bc25eba278	2026-10-31 11:40:48.512723+00	2026-10-31 11:40:49.707324+00	2026-10-31 11:40:48.33233+00	2026-10-31 11:40:49.709142+00
3	4	150000.00	VND	REFUNDED	mock	MP-5065AD72F29A	http://localhost:8080/mock-payment/checkout/MP-5065AD72F29A	\N	974576b3088449608c6df226b61b1e2a	2026-10-31 11:42:10.320199+00	2026-10-31 11:42:11.497617+00	2026-10-31 11:42:10.177192+00	2026-10-31 11:42:11.499588+00
4	5	150000.00	VND	REFUNDED	mock	MP-96DCFD4C1428	http://localhost:8080/mock-payment/checkout/MP-96DCFD4C1428	\N	0892e32ae07d4bf985dd77accbd9d117	2026-10-31 12:02:20.976584+00	2026-10-31 12:02:22.113242+00	2026-10-31 12:02:20.836225+00	2026-10-31 12:02:22.114539+00
5	6	150000.00	VND	PAID	mock	MP-E0E30DEB96CB	http://localhost:8080/mock-payment/checkout/MP-E0E30DEB96CB	\N	c16ce70b1d9e4e1c90b6c486353f6f42	2026-11-07 01:48:29.532878+00	\N	2026-11-07 01:48:29.502825+00	2026-11-07 01:48:29.566435+00
6	7	150000.00	VND	REFUNDED	mock	MP-169DA6E8872C	http://localhost:8080/mock-payment/checkout/MP-169DA6E8872C	\N	98dea078a71d4843a085aec7611b10ad	2026-11-07 01:48:29.849374+00	2026-11-07 01:48:29.895773+00	2026-11-07 01:48:29.832629+00	2026-11-07 01:48:29.897404+00
7	8	150000.00	VND	FAILED	mock	MP-F3D173435DA1	http://localhost:8080/mock-payment/checkout/MP-F3D173435DA1	Card declined (sandbox)	68637bfe52e045239b227af1215ababc	\N	\N	2026-11-07 01:48:30.017824+00	2026-11-07 01:48:30.049097+00
8	8	150000.00	VND	PENDING	mock	MP-4B0FC56CDE53	http://localhost:8080/mock-payment/checkout/MP-4B0FC56CDE53	\N	\N	\N	\N	2026-11-07 01:48:30.065563+00	2026-11-07 01:48:30.068545+00
\.


--
-- Data for Name: recommendation_logs; Type: TABLE DATA; Schema: public; Owner: healthcare
--

COPY public.recommendation_logs (id, specialty_id, created_at) FROM stdin;
1	7	2026-10-31 11:33:34.389993+00
2	2	2026-10-31 11:34:58.946994+00
3	3	2026-10-31 11:34:58.946997+00
4	1	2026-10-31 11:34:58.946998+00
5	3	2026-10-31 11:40:38.370529+00
6	1	2026-10-31 11:40:38.370533+00
7	2	2026-10-31 11:40:45.595495+00
8	3	2026-10-31 11:40:45.595502+00
9	1	2026-10-31 11:40:45.595502+00
10	3	2026-10-31 11:41:15.710013+00
11	1	2026-10-31 11:41:15.710018+00
12	2	2026-10-31 11:42:07.400456+00
13	3	2026-10-31 11:42:07.40046+00
14	1	2026-10-31 11:42:07.40046+00
15	1	2026-10-31 11:42:55.930939+00
16	3	2026-10-31 11:49:20.708762+00
17	6	2026-10-31 11:49:20.70877+00
18	7	2026-10-31 11:49:20.708772+00
19	7	2026-10-31 11:59:39.044475+00
20	2	2026-10-31 12:02:10.95549+00
21	1	2026-10-31 12:02:10.955494+00
22	2	2026-10-31 12:02:13.424227+00
23	1	2026-10-31 12:02:13.424237+00
24	11	2026-10-31 12:02:14.812871+00
25	10	2026-10-31 12:02:14.812875+00
26	1	2026-10-31 12:02:14.812875+00
27	2	2026-10-31 12:02:18.085293+00
28	3	2026-10-31 12:02:18.085297+00
29	1	2026-10-31 12:02:18.085297+00
30	8	2026-10-31 12:03:07.464052+00
31	8	2026-11-01 05:53:56.335915+00
32	3	2026-11-01 05:53:56.335925+00
33	7	2026-11-01 05:53:56.335926+00
34	2	2026-11-07 01:48:29.096778+00
35	3	2026-11-07 01:48:29.096781+00
36	1	2026-11-07 01:48:29.096782+00
37	5	2026-11-07 01:48:29.110348+00
\.


--
-- Data for Name: reviews; Type: TABLE DATA; Schema: public; Owner: healthcare
--

COPY public.reviews (id, appointment_id, patient_id, doctor_id, rating, comment, status, moderated_by, moderation_note, created_at, updated_at) FROM stdin;
1	6	1	23	5	Very clear explanations.	PUBLISHED	1	\N	2026-11-07 01:48:29.707464+00	2026-11-07 01:48:30.234006+00
\.


--
-- Data for Name: specialties; Type: TABLE DATA; Schema: public; Owner: healthcare
--

COPY public.specialties (id, name, description, is_active, created_at, updated_at) FROM stdin;
1	General Internal Medicine	First point of contact for general adult health concerns.	t	2026-10-31 11:28:57.830728+00	2026-10-31 11:28:57.830731+00
2	Respiratory Medicine	Lungs and breathing.	t	2026-10-31 11:28:57.830732+00	2026-10-31 11:28:57.830733+00
3	Cardiology	Heart and circulation.	t	2026-10-31 11:28:57.830733+00	2026-10-31 11:28:57.830734+00
4	Gastroenterology	Digestive system.	t	2026-10-31 11:28:57.830734+00	2026-10-31 11:28:57.830734+00
5	Dermatology	Skin, hair and nails.	t	2026-10-31 11:28:57.830735+00	2026-10-31 11:28:57.830735+00
6	Ophthalmology	Eyes and vision.	t	2026-10-31 11:28:57.830735+00	2026-10-31 11:28:57.830736+00
7	Orthopedics	Bones, joints and muscles.	t	2026-10-31 11:28:57.830736+00	2026-10-31 11:28:57.830736+00
8	Rheumatology	Inflammatory joint and autoimmune conditions.	t	2026-10-31 11:28:57.830737+00	2026-10-31 11:28:57.830737+00
9	Otorhinolaryngology (ENT)	Ear, nose and throat.	t	2026-10-31 11:28:57.830737+00	2026-10-31 11:28:57.830737+00
10	Neurology	Brain and nervous system.	t	2026-10-31 11:28:57.830738+00	2026-10-31 11:28:57.830738+00
11	Pediatrics	Children's health.	t	2026-10-31 11:28:57.830738+00	2026-10-31 11:28:57.830739+00
12	E2E Specialty 1793446506219	\N	t	2026-10-31 11:35:06.257044+00	2026-10-31 11:35:06.257047+00
13	E2E Specialty 1793446852626	\N	t	2026-10-31 11:40:52.660636+00	2026-10-31 11:40:52.660641+00
14	E2E Specialty 1793446934389	\N	t	2026-10-31 11:42:14.426629+00	2026-10-31 11:42:14.426632+00
15	E2E Specialty 1793448144948	\N	t	2026-10-31 12:02:24.982845+00	2026-10-31 12:02:24.982848+00
\.


--
-- Data for Name: symptom_specialty_rules; Type: TABLE DATA; Schema: public; Owner: healthcare
--

COPY public.symptom_specialty_rules (id, symptom_id, specialty_id, weight) FROM stdin;
1	1	2	1
2	1	1	0.3
3	2	2	1
4	2	3	0.6
5	3	3	1
6	3	1	0.3
7	4	3	1
8	5	5	1
9	6	5	0.8
10	7	5	1
11	8	7	0.8
12	8	8	0.8
13	9	8	1
14	10	7	1
15	11	6	1
16	12	6	1
17	13	6	1
18	13	10	0.6
19	14	4	1
20	14	1	0.3
21	15	4	1
22	16	4	1
23	17	9	1
24	17	1	0.3
25	18	9	1
26	19	10	0.8
27	19	1	0.5
28	20	10	1
29	21	1	1
30	21	11	0.3
31	22	11	1
32	23	1	1
\.


--
-- Data for Name: symptoms; Type: TABLE DATA; Schema: public; Owner: healthcare
--

COPY public.symptoms (id, name, description, keywords, is_red_flag, red_flag_message, is_active, created_at, updated_at) FROM stdin;
1	Persistent cough	\N	cough,coughing	f	\N	t	2026-10-31 11:28:57.866049+00	2026-10-31 11:28:57.866051+00
2	Shortness of breath	\N	breathless,short of breath,difficulty breathing	t	Severe or sudden difficulty breathing needs urgent medical attention.	t	2026-10-31 11:28:57.867035+00	2026-10-31 11:28:57.867036+00
3	Chest pain	\N	chest tightness,chest pressure	t	Chest pain can be a sign of a serious heart problem.	t	2026-10-31 11:28:57.86899+00	2026-10-31 11:28:57.868994+00
4	Palpitations	\N	racing heart,irregular heartbeat	f	\N	t	2026-10-31 11:28:57.870869+00	2026-10-31 11:28:57.870873+00
5	Skin rash	\N	rash,hives	f	\N	t	2026-10-31 11:28:57.872308+00	2026-10-31 11:28:57.87231+00
6	Itching	\N	itchy,itch	f	\N	t	2026-10-31 11:28:57.874152+00	2026-10-31 11:28:57.874155+00
7	Acne	\N	pimples,breakouts	f	\N	t	2026-10-31 11:28:57.874923+00	2026-10-31 11:28:57.874924+00
8	Joint pain	\N	knee pain,arthritis,painful joints	f	\N	t	2026-10-31 11:28:57.875445+00	2026-10-31 11:28:57.875446+00
9	Morning joint stiffness	\N	stiff joints	f	\N	t	2026-10-31 11:28:57.875953+00	2026-10-31 11:28:57.875954+00
10	Back pain	\N	lower back pain,backache	f	\N	t	2026-10-31 11:28:57.876829+00	2026-10-31 11:28:57.876831+00
11	Eye discomfort	\N	eye pain,red eye,eye irritation	f	\N	t	2026-10-31 11:28:57.877429+00	2026-10-31 11:28:57.87743+00
12	Blurred vision	\N	blurry vision,blurred	f	\N	t	2026-10-31 11:28:57.878579+00	2026-10-31 11:28:57.87858+00
13	Sudden loss of vision	\N	vision loss,cannot see	t	Sudden loss of vision is a medical emergency.	t	2026-10-31 11:28:57.879507+00	2026-10-31 11:28:57.879511+00
14	Stomach pain	\N	abdominal pain,stomach ache,stomachache	f	\N	t	2026-10-31 11:28:57.880322+00	2026-10-31 11:28:57.880328+00
15	Heartburn	\N	acid reflux,indigestion	f	\N	t	2026-10-31 11:28:57.881554+00	2026-10-31 11:28:57.881555+00
16	Diarrhea	\N	loose stools	f	\N	t	2026-10-31 11:28:57.8823+00	2026-10-31 11:28:57.882301+00
17	Sore throat	\N	throat pain	f	\N	t	2026-10-31 11:28:57.883162+00	2026-10-31 11:28:57.883164+00
18	Ear pain	\N	earache	f	\N	t	2026-10-31 11:28:57.883792+00	2026-10-31 11:28:57.883794+00
19	Headache	\N	migraine	f	\N	t	2026-10-31 11:28:57.884514+00	2026-10-31 11:28:57.884515+00
20	Sudden weakness or numbness on one side	\N	numbness,slurred speech,facial drooping	t	Sudden one-sided weakness, numbness or difficulty speaking can be signs of a stroke.	t	2026-10-31 11:28:57.885369+00	2026-10-31 11:28:57.885371+00
21	Fever	\N	high temperature	f	\N	t	2026-10-31 11:28:57.886065+00	2026-10-31 11:28:57.886066+00
22	Fever in a child	\N	child fever,baby fever	f	\N	t	2026-10-31 11:28:57.88663+00	2026-10-31 11:28:57.886631+00
23	Fatigue	\N	tired,tiredness,exhaustion	f	\N	t	2026-10-31 11:28:57.887321+00	2026-10-31 11:28:57.887322+00
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: healthcare
--

COPY public.users (id, email, password_hash, role, account_status, last_login_at, created_at, updated_at) FROM stdin;
3	e2e-1793446499120@example.com	$argon2id$v=19$m=65536,t=3,p=4$f1OJmvEIF6UWdVV/Yx1dLQ$aGBQoTI9xbL7WMV3JYz4x2R3bV5atumkkxkfJX+gPyY	PATIENT	ACTIVE	\N	2026-10-31 11:34:59.90916+00	2026-10-31 11:34:59.909164+00
4	e2e-1793446845767@example.com	$argon2id$v=19$m=65536,t=3,p=4$vL/VxemZa8/tDYAUSh1P0g$k85vdkJkTRftmCJQp6hQ0jrAan8uDoDw4FXz5M1EgDA	PATIENT	ACTIVE	\N	2026-10-31 11:40:46.391883+00	2026-10-31 11:40:46.391888+00
5	e2e-1793446927569@example.com	$argon2id$v=19$m=65536,t=3,p=4$fyuGOVSXYtnrxqT3BxTiKA$jAQPStuu2gX5JuTNtoRitythRreaCho2/wbgDB9CzhU	PATIENT	ACTIVE	\N	2026-10-31 11:42:08.218911+00	2026-10-31 11:42:08.218914+00
6	e2e-1793448138264@example.com	$argon2id$v=19$m=65536,t=3,p=4$FfGwuiPG0o/PFHXXEbz3Ng$1hsMtR0k7xdsA7E0/AXuuNY2EBIrC5vndv7ZxjPhodg	PATIENT	ACTIVE	\N	2026-10-31 12:02:18.89654+00	2026-10-31 12:02:18.896545+00
1	admin@example.com	$argon2id$v=19$m=65536,t=3,p=4$H9zVb6YemcRUvnaAun4iHA$fMBx384RpOXUI1FjxTBlpVSEbq+TbNxeif9rSKqGqQs	ADMIN	ACTIVE	2026-11-07 01:48:30.184646+00	2026-10-31 11:28:57.958599+00	2026-11-07 01:48:30.184907+00
7	smoke-1eb3ef90@example.com	$argon2id$v=19$m=65536,t=3,p=4$pWMY8ouVUl0aQJeiycrsog$eT8nVwAwWfWxQmlMmdXG3pvPezrAqBjbqzD7/QyYpms	PATIENT	INACTIVE	\N	2026-11-07 01:48:29.205693+00	2026-11-07 01:48:30.549001+00
2	patient@example.com	$argon2id$v=19$m=65536,t=3,p=4$fhKa6yMsl+3fDBDN3fGQ4w$UmWBO8fwbunags8mS+jKmAKTyDKz1Qk6A9tk/eCfXFg	PATIENT	ACTIVE	2026-11-07 01:48:30.78288+00	2026-10-31 11:28:58.026527+00	2026-11-07 01:48:30.783142+00
8	nguyenhoang1362005@gmail.com	$argon2id$v=19$m=65536,t=3,p=4$jsUUB0Nrsxp9yPTENMP8IQ$IQc15FvH+WoQsDw2U4ZtT/1x9/N+zmKtUb+E/zjB5aQ	PATIENT	ACTIVE	\N	2026-11-07 01:49:48.096996+00	2026-11-07 01:49:48.097+00
\.


--
-- Name: appointment_status_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: healthcare
--

SELECT pg_catalog.setval('public.appointment_status_history_id_seq', 25, true);


--
-- Name: appointment_types_id_seq; Type: SEQUENCE SET; Schema: public; Owner: healthcare
--

SELECT pg_catalog.setval('public.appointment_types_id_seq', 6, true);


--
-- Name: appointments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: healthcare
--

SELECT pg_catalog.setval('public.appointments_id_seq', 8, true);


--
-- Name: audit_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: healthcare
--

SELECT pg_catalog.setval('public.audit_logs_id_seq', 63, true);


--
-- Name: departments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: healthcare
--

SELECT pg_catalog.setval('public.departments_id_seq', 14, true);


--
-- Name: doctor_schedules_id_seq; Type: SEQUENCE SET; Schema: public; Owner: healthcare
--

SELECT pg_catalog.setval('public.doctor_schedules_id_seq', 6132, true);


--
-- Name: doctors_id_seq; Type: SEQUENCE SET; Schema: public; Owner: healthcare
--

SELECT pg_catalog.setval('public.doctors_id_seq', 28, true);


--
-- Name: hospitals_id_seq; Type: SEQUENCE SET; Schema: public; Owner: healthcare
--

SELECT pg_catalog.setval('public.hospitals_id_seq', 4, true);


--
-- Name: notifications_id_seq; Type: SEQUENCE SET; Schema: public; Owner: healthcare
--

SELECT pg_catalog.setval('public.notifications_id_seq', 33, true);


--
-- Name: patient_profiles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: healthcare
--

SELECT pg_catalog.setval('public.patient_profiles_id_seq', 7, true);


--
-- Name: payments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: healthcare
--

SELECT pg_catalog.setval('public.payments_id_seq', 8, true);


--
-- Name: recommendation_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: healthcare
--

SELECT pg_catalog.setval('public.recommendation_logs_id_seq', 37, true);


--
-- Name: reviews_id_seq; Type: SEQUENCE SET; Schema: public; Owner: healthcare
--

SELECT pg_catalog.setval('public.reviews_id_seq', 1, true);


--
-- Name: specialties_id_seq; Type: SEQUENCE SET; Schema: public; Owner: healthcare
--

SELECT pg_catalog.setval('public.specialties_id_seq', 15, true);


--
-- Name: symptom_specialty_rules_id_seq; Type: SEQUENCE SET; Schema: public; Owner: healthcare
--

SELECT pg_catalog.setval('public.symptom_specialty_rules_id_seq', 32, true);


--
-- Name: symptoms_id_seq; Type: SEQUENCE SET; Schema: public; Owner: healthcare
--

SELECT pg_catalog.setval('public.symptoms_id_seq', 23, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: healthcare
--

SELECT pg_catalog.setval('public.users_id_seq', 8, true);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: appointment_status_history appointment_status_history_pkey; Type: CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.appointment_status_history
    ADD CONSTRAINT appointment_status_history_pkey PRIMARY KEY (id);


--
-- Name: appointment_types appointment_types_pkey; Type: CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.appointment_types
    ADD CONSTRAINT appointment_types_pkey PRIMARY KEY (id);


--
-- Name: appointments appointments_booking_reference_key; Type: CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.appointments
    ADD CONSTRAINT appointments_booking_reference_key UNIQUE (booking_reference);


--
-- Name: appointments appointments_pkey; Type: CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.appointments
    ADD CONSTRAINT appointments_pkey PRIMARY KEY (id);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);


--
-- Name: departments departments_pkey; Type: CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.departments
    ADD CONSTRAINT departments_pkey PRIMARY KEY (id);


--
-- Name: doctor_schedules doctor_schedules_pkey; Type: CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.doctor_schedules
    ADD CONSTRAINT doctor_schedules_pkey PRIMARY KEY (id);


--
-- Name: doctors doctors_erp_doctor_id_key; Type: CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.doctors
    ADD CONSTRAINT doctors_erp_doctor_id_key UNIQUE (erp_doctor_id);


--
-- Name: doctors doctors_pkey; Type: CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.doctors
    ADD CONSTRAINT doctors_pkey PRIMARY KEY (id);


--
-- Name: hospitals hospitals_pkey; Type: CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.hospitals
    ADD CONSTRAINT hospitals_pkey PRIMARY KEY (id);


--
-- Name: appointments no_overlap; Type: CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.appointments
    ADD CONSTRAINT no_overlap EXCLUDE USING gist (doctor_id WITH =, tstzrange(start_time, end_with_buffer) WITH &&) WHERE (((status)::text = ANY ((ARRAY['PENDING'::character varying, 'CONFIRMED'::character varying])::text[])));


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


--
-- Name: patient_profiles patient_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.patient_profiles
    ADD CONSTRAINT patient_profiles_pkey PRIMARY KEY (id);


--
-- Name: patient_profiles patient_profiles_user_id_key; Type: CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.patient_profiles
    ADD CONSTRAINT patient_profiles_user_id_key UNIQUE (user_id);


--
-- Name: payments payments_pkey; Type: CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_pkey PRIMARY KEY (id);


--
-- Name: payments payments_provider_reference_key; Type: CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_provider_reference_key UNIQUE (provider_reference);


--
-- Name: recommendation_logs recommendation_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.recommendation_logs
    ADD CONSTRAINT recommendation_logs_pkey PRIMARY KEY (id);


--
-- Name: reviews reviews_appointment_id_key; Type: CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_appointment_id_key UNIQUE (appointment_id);


--
-- Name: reviews reviews_pkey; Type: CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_pkey PRIMARY KEY (id);


--
-- Name: specialties specialties_name_key; Type: CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.specialties
    ADD CONSTRAINT specialties_name_key UNIQUE (name);


--
-- Name: specialties specialties_pkey; Type: CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.specialties
    ADD CONSTRAINT specialties_pkey PRIMARY KEY (id);


--
-- Name: symptom_specialty_rules symptom_specialty_rules_pkey; Type: CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.symptom_specialty_rules
    ADD CONSTRAINT symptom_specialty_rules_pkey PRIMARY KEY (id);


--
-- Name: symptoms symptoms_name_key; Type: CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.symptoms
    ADD CONSTRAINT symptoms_name_key UNIQUE (name);


--
-- Name: symptoms symptoms_pkey; Type: CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.symptoms
    ADD CONSTRAINT symptoms_pkey PRIMARY KEY (id);


--
-- Name: symptom_specialty_rules uq_symptom_specialty; Type: CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.symptom_specialty_rules
    ADD CONSTRAINT uq_symptom_specialty UNIQUE (symptom_id, specialty_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_appointment_status_history_appointment_id; Type: INDEX; Schema: public; Owner: healthcare
--

CREATE INDEX ix_appointment_status_history_appointment_id ON public.appointment_status_history USING btree (appointment_id);


--
-- Name: ix_appointment_types_doctor_id; Type: INDEX; Schema: public; Owner: healthcare
--

CREATE INDEX ix_appointment_types_doctor_id ON public.appointment_types USING btree (doctor_id);


--
-- Name: ix_appointment_types_specialty_id; Type: INDEX; Schema: public; Owner: healthcare
--

CREATE INDEX ix_appointment_types_specialty_id ON public.appointment_types USING btree (specialty_id);


--
-- Name: ix_appointments_doctor_start; Type: INDEX; Schema: public; Owner: healthcare
--

CREATE INDEX ix_appointments_doctor_start ON public.appointments USING btree (doctor_id, start_time);


--
-- Name: ix_appointments_erp_booking_id; Type: INDEX; Schema: public; Owner: healthcare
--

CREATE INDEX ix_appointments_erp_booking_id ON public.appointments USING btree (erp_booking_id);


--
-- Name: ix_appointments_patient_id; Type: INDEX; Schema: public; Owner: healthcare
--

CREATE INDEX ix_appointments_patient_id ON public.appointments USING btree (patient_id);


--
-- Name: ix_appointments_status; Type: INDEX; Schema: public; Owner: healthcare
--

CREATE INDEX ix_appointments_status ON public.appointments USING btree (status);


--
-- Name: ix_audit_logs_action; Type: INDEX; Schema: public; Owner: healthcare
--

CREATE INDEX ix_audit_logs_action ON public.audit_logs USING btree (action);


--
-- Name: ix_audit_logs_created_at; Type: INDEX; Schema: public; Owner: healthcare
--

CREATE INDEX ix_audit_logs_created_at ON public.audit_logs USING btree (created_at);


--
-- Name: ix_departments_hospital_id; Type: INDEX; Schema: public; Owner: healthcare
--

CREATE INDEX ix_departments_hospital_id ON public.departments USING btree (hospital_id);


--
-- Name: ix_departments_specialty_id; Type: INDEX; Schema: public; Owner: healthcare
--

CREATE INDEX ix_departments_specialty_id ON public.departments USING btree (specialty_id);


--
-- Name: ix_doctor_schedules_doctor_start; Type: INDEX; Schema: public; Owner: healthcare
--

CREATE INDEX ix_doctor_schedules_doctor_start ON public.doctor_schedules USING btree (doctor_id, start_time);


--
-- Name: ix_doctors_department_id; Type: INDEX; Schema: public; Owner: healthcare
--

CREATE INDEX ix_doctors_department_id ON public.doctors USING btree (department_id);


--
-- Name: ix_doctors_full_name; Type: INDEX; Schema: public; Owner: healthcare
--

CREATE INDEX ix_doctors_full_name ON public.doctors USING btree (full_name);


--
-- Name: ix_doctors_hospital_id; Type: INDEX; Schema: public; Owner: healthcare
--

CREATE INDEX ix_doctors_hospital_id ON public.doctors USING btree (hospital_id);


--
-- Name: ix_hospitals_city; Type: INDEX; Schema: public; Owner: healthcare
--

CREATE INDEX ix_hospitals_city ON public.hospitals USING btree (city);


--
-- Name: ix_hospitals_name; Type: INDEX; Schema: public; Owner: healthcare
--

CREATE INDEX ix_hospitals_name ON public.hospitals USING btree (name);


--
-- Name: ix_notifications_user_created; Type: INDEX; Schema: public; Owner: healthcare
--

CREATE INDEX ix_notifications_user_created ON public.notifications USING btree (user_id, created_at);


--
-- Name: ix_payments_appointment_id; Type: INDEX; Schema: public; Owner: healthcare
--

CREATE INDEX ix_payments_appointment_id ON public.payments USING btree (appointment_id);


--
-- Name: ix_recommendation_logs_created_at; Type: INDEX; Schema: public; Owner: healthcare
--

CREATE INDEX ix_recommendation_logs_created_at ON public.recommendation_logs USING btree (created_at);


--
-- Name: ix_reviews_doctor_id; Type: INDEX; Schema: public; Owner: healthcare
--

CREATE INDEX ix_reviews_doctor_id ON public.reviews USING btree (doctor_id);


--
-- Name: ix_reviews_patient_id; Type: INDEX; Schema: public; Owner: healthcare
--

CREATE INDEX ix_reviews_patient_id ON public.reviews USING btree (patient_id);


--
-- Name: ix_symptom_specialty_rules_specialty_id; Type: INDEX; Schema: public; Owner: healthcare
--

CREATE INDEX ix_symptom_specialty_rules_specialty_id ON public.symptom_specialty_rules USING btree (specialty_id);


--
-- Name: ix_symptom_specialty_rules_symptom_id; Type: INDEX; Schema: public; Owner: healthcare
--

CREATE INDEX ix_symptom_specialty_rules_symptom_id ON public.symptom_specialty_rules USING btree (symptom_id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: healthcare
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: appointment_status_history appointment_status_history_appointment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.appointment_status_history
    ADD CONSTRAINT appointment_status_history_appointment_id_fkey FOREIGN KEY (appointment_id) REFERENCES public.appointments(id) ON DELETE CASCADE;


--
-- Name: appointment_types appointment_types_doctor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.appointment_types
    ADD CONSTRAINT appointment_types_doctor_id_fkey FOREIGN KEY (doctor_id) REFERENCES public.doctors(id);


--
-- Name: appointment_types appointment_types_specialty_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.appointment_types
    ADD CONSTRAINT appointment_types_specialty_id_fkey FOREIGN KEY (specialty_id) REFERENCES public.specialties(id);


--
-- Name: appointments appointments_appointment_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.appointments
    ADD CONSTRAINT appointments_appointment_type_id_fkey FOREIGN KEY (appointment_type_id) REFERENCES public.appointment_types(id);


--
-- Name: appointments appointments_doctor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.appointments
    ADD CONSTRAINT appointments_doctor_id_fkey FOREIGN KEY (doctor_id) REFERENCES public.doctors(id);


--
-- Name: appointments appointments_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.appointments
    ADD CONSTRAINT appointments_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patient_profiles(id);


--
-- Name: departments departments_hospital_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.departments
    ADD CONSTRAINT departments_hospital_id_fkey FOREIGN KEY (hospital_id) REFERENCES public.hospitals(id);


--
-- Name: departments departments_specialty_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.departments
    ADD CONSTRAINT departments_specialty_id_fkey FOREIGN KEY (specialty_id) REFERENCES public.specialties(id);


--
-- Name: doctor_schedules doctor_schedules_doctor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.doctor_schedules
    ADD CONSTRAINT doctor_schedules_doctor_id_fkey FOREIGN KEY (doctor_id) REFERENCES public.doctors(id) ON DELETE CASCADE;


--
-- Name: doctors doctors_department_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.doctors
    ADD CONSTRAINT doctors_department_id_fkey FOREIGN KEY (department_id) REFERENCES public.departments(id);


--
-- Name: doctors doctors_hospital_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.doctors
    ADD CONSTRAINT doctors_hospital_id_fkey FOREIGN KEY (hospital_id) REFERENCES public.hospitals(id);


--
-- Name: notifications notifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: patient_profiles patient_profiles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.patient_profiles
    ADD CONSTRAINT patient_profiles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: payments payments_appointment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_appointment_id_fkey FOREIGN KEY (appointment_id) REFERENCES public.appointments(id);


--
-- Name: recommendation_logs recommendation_logs_specialty_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.recommendation_logs
    ADD CONSTRAINT recommendation_logs_specialty_id_fkey FOREIGN KEY (specialty_id) REFERENCES public.specialties(id) ON DELETE CASCADE;


--
-- Name: reviews reviews_appointment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_appointment_id_fkey FOREIGN KEY (appointment_id) REFERENCES public.appointments(id);


--
-- Name: reviews reviews_doctor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_doctor_id_fkey FOREIGN KEY (doctor_id) REFERENCES public.doctors(id);


--
-- Name: reviews reviews_moderated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_moderated_by_fkey FOREIGN KEY (moderated_by) REFERENCES public.users(id);


--
-- Name: reviews reviews_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patient_profiles(id);


--
-- Name: symptom_specialty_rules symptom_specialty_rules_specialty_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.symptom_specialty_rules
    ADD CONSTRAINT symptom_specialty_rules_specialty_id_fkey FOREIGN KEY (specialty_id) REFERENCES public.specialties(id) ON DELETE CASCADE;


--
-- Name: symptom_specialty_rules symptom_specialty_rules_symptom_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: healthcare
--

ALTER TABLE ONLY public.symptom_specialty_rules
    ADD CONSTRAINT symptom_specialty_rules_symptom_id_fkey FOREIGN KEY (symptom_id) REFERENCES public.symptoms(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

