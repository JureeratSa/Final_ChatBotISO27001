-- TUH Chatbot AI — ตารางบน Microsoft SQL Server
-- สร้างอัตโนมัติจาก app/models/models.py ด้วย scripts/generate_sqlserver_schema.py — อย่าแก้มือ
-- ตรงกับ Alembic revision d1f3a5c7e9b2 (schema เดียวกับ TiDB)
-- รันบนฐานข้อมูลว่าง: sqlcmd -S <host> -d <db> -U <user> -i 001_create_tables.sql
SET XACT_ABORT ON;
BEGIN TRANSACTION;

CREATE TABLE forms (
	id NVARCHAR(255) NOT NULL, 
	name NVARCHAR(255) NOT NULL, 
	filename NVARCHAR(255) NULL, 
	page NVARCHAR(50) NULL, 
	download_link NVARCHAR(2048) NULL, 
	department NVARCHAR(100) NULL, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_forms_department ON forms (department);

CREATE TABLE history (
	id NVARCHAR(255) NOT NULL, 
	query NVARCHAR(max) NULL, 
	answer NVARCHAR(max) NULL, 
	response_time FLOAT NULL, 
	chunk_ids NVARCHAR(max) NULL, 
	api_model NVARCHAR(255) NULL, 
	referenced_docs NVARCHAR(max) NULL, 
	cited_docs NVARCHAR(max) NULL, 
	timestamp DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(), 
	PRIMARY KEY (id)
);

CREATE TABLE settings (
	id NVARCHAR(50) NOT NULL, 
	model_name NVARCHAR(100) NOT NULL, 
	temperature FLOAT NOT NULL, 
	max_tokens INTEGER NOT NULL, 
	top_k INTEGER NOT NULL, 
	embedding_tech NVARCHAR(50) NOT NULL, 
	system_prompt NVARCHAR(max) NULL, 
	welcome_message NVARCHAR(max) NULL, 
	chat_greeting NVARCHAR(max) NULL, 
	custom_faqs NVARCHAR(max) NULL, 
	predefined_faqs NVARCHAR(max) NULL, 
	last_build_duration FLOAT NULL, 
	gemini_api_key NVARCHAR(500) NULL, 
	rebuild_status NVARCHAR(50) NOT NULL, 
	rebuild_message NVARCHAR(max) NULL, 
	updated_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(), 
	PRIMARY KEY (id)
);

CREATE TABLE users (
	id INTEGER NOT NULL IDENTITY, 
	username NVARCHAR(100) NOT NULL, 
	password_hash NVARCHAR(255) NOT NULL, 
	display_name NVARCHAR(100) NOT NULL, 
	role NVARCHAR(50) NOT NULL, 
	department NVARCHAR(100) NULL, 
	is_active BIT NOT NULL, 
	password_changed_at DATETIMEOFFSET NULL DEFAULT SYSDATETIMEOFFSET(), 
	token_version INTEGER NOT NULL DEFAULT '0', 
	created_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(), 
	updated_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(), 
	PRIMARY KEY (id)
);
CREATE UNIQUE INDEX ix_users_username ON users (username);

CREATE TABLE admin_audit_logs (
	id INTEGER NOT NULL IDENTITY, 
	timestamp DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(), 
	user_id INTEGER NULL, 
	username NVARCHAR(100) NULL, 
	department NVARCHAR(100) NULL, 
	action NVARCHAR(50) NOT NULL, 
	method NVARCHAR(10) NULL, 
	path NVARCHAR(500) NULL, 
	status_code INTEGER NULL, 
	ip_address NVARCHAR(64) NULL, 
	user_agent NVARCHAR(500) NULL, 
	detail NVARCHAR(max) NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);
CREATE INDEX ix_admin_audit_logs_action ON admin_audit_logs (action);
CREATE INDEX ix_admin_audit_logs_timestamp ON admin_audit_logs (timestamp);
CREATE INDEX ix_admin_audit_logs_user_id ON admin_audit_logs (user_id);

CREATE TABLE announcements (
	id INTEGER NOT NULL IDENTITY, 
	title NVARCHAR(255) NOT NULL, 
	content NVARCHAR(max) NULL, 
	start_date NVARCHAR(100) NULL, 
	end_date NVARCHAR(100) NULL, 
	category NVARCHAR(100) NULL, 
	created_by NVARCHAR(100) NULL, 
	created_by_id INTEGER NULL, 
	pinned BIT NOT NULL, 
	created_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(created_by_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE documents (
	id INTEGER NOT NULL IDENTITY, 
	filename NVARCHAR(255) NOT NULL, 
	display_name NVARCHAR(255) NULL, 
	status NVARCHAR(50) NOT NULL, 
	pages INTEGER NULL, 
	size INTEGER NULL, 
	exclude_pages NVARCHAR(max) NULL, 
	chunking_duration FLOAT NULL, 
	embedding_duration FLOAT NULL, 
	upload_date DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(), 
	uploaded_by NVARCHAR(100) NULL, 
	uploaded_by_id INTEGER NULL, 
	department NVARCHAR(100) NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(uploaded_by_id) REFERENCES users (id) ON DELETE SET NULL
);
CREATE INDEX ix_documents_department ON documents (department);
CREATE UNIQUE INDEX ix_documents_filename ON documents (filename);

CREATE TABLE feedback (
	id NVARCHAR(255) NOT NULL, 
	rating NVARCHAR(50) NOT NULL, 
	stars INTEGER NULL, 
	comment NVARCHAR(max) NULL, 
	query NVARCHAR(max) NULL, 
	answer NVARCHAR(max) NULL, 
	history_id NVARCHAR(255) NULL, 
	timestamp DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(history_id) REFERENCES history (id) ON DELETE SET NULL
);

CREATE TABLE unanswered (
	id NVARCHAR(255) NOT NULL, 
	query NVARCHAR(max) NOT NULL, 
	count INTEGER NOT NULL, 
	status NVARCHAR(50) NOT NULL, 
	resolution_type NVARCHAR(50) NULL, 
	search_keywords NVARCHAR(max) NULL, 
	ignore_reason NVARCHAR(50) NULL, 
	note NVARCHAR(max) NULL, 
	resolved_by_id INTEGER NULL, 
	resolved_at DATETIMEOFFSET NULL, 
	department NVARCHAR(100) NULL, 
	timestamp DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(), 
	updated_at DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(resolved_by_id) REFERENCES users (id) ON DELETE SET NULL
);
CREATE INDEX ix_unanswered_department ON unanswered (department);

CREATE TABLE alembic_version (
	version_num VARCHAR(32) NOT NULL,
	CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
INSERT INTO alembic_version (version_num) VALUES ('d1f3a5c7e9b2');

COMMIT;
