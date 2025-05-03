-- sample_saas_dump.sql

-- Create plans table
CREATE TABLE plans (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    password_hash VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create projects table
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    name VARCHAR(255),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create subscriptions table
CREATE TABLE subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    plan_id INT REFERENCES plans(id),
    status VARCHAR(20),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP
);

-- Create payments table
CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    amount DECIMAL(10, 2),
    status VARCHAR(20),
    paid_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample plans
INSERT INTO plans (name, price) VALUES
('Free', 0.00),
('Pro', 29.99),
('Enterprise', 99.99);

-- Insert sample users
INSERT INTO users (email, name, password_hash) VALUES
('alice@example.com', 'Alice', 'hashedpassword1'),
('bob@example.com', 'Bob', 'hashedpassword2');

-- Insert sample projects
INSERT INTO projects (user_id, name, description) VALUES
(1, 'Alice Project', 'First project by Alice'),
(2, 'Bob Project', 'First project by Bob');

-- Insert sample subscriptions
INSERT INTO subscriptions (user_id, plan_id, status) VALUES
(1, 2, 'active'),
(2, 1, 'trial');

-- Insert sample payments
INSERT INTO payments (user_id, amount, status) VALUES
(1, 29.99, 'paid'),
(2, 0.00, 'trial');
