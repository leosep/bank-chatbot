-- SQL script to recreate all MariaDB tables for the bank-chatbot project

-- Table: users
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    password VARCHAR(200) NOT NULL
);

-- Table: calls
CREATE TABLE calls (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sender_id VARCHAR(200) NOT NULL,
    full_name VARCHAR(200) NOT NULL,
    phone VARCHAR(50) NOT NULL,
    preferred_time VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'Pending',
    resolution TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME
);

-- Table: user_sessions
CREATE TABLE user_sessions (
    sender_id VARCHAR(255) PRIMARY KEY,
    employee_id VARCHAR(255),
    is_verified BOOLEAN DEFAULT FALSE,
    last_active DATETIME DEFAULT CURRENT_TIMESTAMP,
    awaiting_code BOOLEAN DEFAULT FALSE,
    provided_cedula VARCHAR(255)
);