CREATE DATABASE IF NOT EXISTS cricpro;
USE cricpro;

-- ============================
-- USER TABLE
-- ============================
CREATE TABLE IF NOT EXISTS user (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE,
    email VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255),
    role VARCHAR(20),
    status VARCHAR(20) DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================
-- PLAYER TABLE
-- ============================
CREATE TABLE IF NOT EXISTS player (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    dob DATE,
    age INT,
    batch_id INT,
    batting_style VARCHAR(50),
    bowling_style VARCHAR(50),
    role_in_team VARCHAR(50),
    bio TEXT,
    profile_completed TINYINT(1) DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES user(id)
);

-- ============================
-- COACH TABLE
-- ============================
CREATE TABLE IF NOT EXISTS coach (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    FOREIGN KEY (user_id) REFERENCES user(id)
);

-- ============================
-- BATCH TABLE
-- ============================
CREATE TABLE IF NOT EXISTS batch (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50),
    min_age INT,
    max_age INT
);

-- ============================
-- MATCH TABLE
-- ============================
CREATE TABLE IF NOT EXISTS `match` (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255),
    match_date DATE,
    format VARCHAR(50),
    scoring_mode VARCHAR(20),

    team_name VARCHAR(100),
    opponent_name VARCHAR(100),

    status VARCHAR(50) DEFAULT 'first_innings',

    scorer_coach_id INT,
    scorer_player_id INT,

    toss_winner VARCHAR(100),
    team_batted_first VARCHAR(100),

    current_innings INT DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (scorer_coach_id) REFERENCES coach(id),
    FOREIGN KEY (scorer_player_id) REFERENCES player(id)
);

-- ============================
-- MATCH ASSIGNMENT (PLAYING 11)
-- ============================
CREATE TABLE IF NOT EXISTS match_assignment (
    id INT AUTO_INCREMENT PRIMARY KEY,
    match_id INT,
    player_id INT,
    FOREIGN KEY (match_id) REFERENCES `match`(id),
    FOREIGN KEY (player_id) REFERENCES player(id)
);

-- ============================
-- OPPONENT TEMP PLAYERS
-- ============================
CREATE TABLE IF NOT EXISTS opponent_temp_player (
    id INT AUTO_INCREMENT PRIMARY KEY,
    match_id INT,
    name VARCHAR(50),
    role VARCHAR(50),
    FOREIGN KEY (match_id) REFERENCES `match`(id)
);

-- ============================
-- MANUAL SCORE TABLE
-- ============================
CREATE TABLE IF NOT EXISTS manual_score (
    id INT AUTO_INCREMENT PRIMARY KEY,
    match_id INT,
    player_id INT,
    innings INT DEFAULT 1,

    runs INT DEFAULT 0,
    balls_faced INT DEFAULT 0,
    fours INT DEFAULT 0,
    sixes INT DEFAULT 0,
    is_out TINYINT(1) DEFAULT 0,

    overs FLOAT DEFAULT 0,
    runs_conceded INT DEFAULT 0,
    wickets INT DEFAULT 0,

    catches INT DEFAULT 0,
    drops INT DEFAULT 0,
    saves INT DEFAULT 0,

    is_opponent TINYINT(1) DEFAULT 0,

    FOREIGN KEY (match_id) REFERENCES `match`(id),
    FOREIGN KEY (player_id) REFERENCES player(id)
);

-- ============================
-- WAGON WHEEL TABLE
-- ============================
CREATE TABLE IF NOT EXISTS wagon_wheel (
    id INT AUTO_INCREMENT PRIMARY KEY,
    match_id INT,
    player_id INT,
    innings INT DEFAULT 1,

    angle FLOAT,
    distance FLOAT,
    runs INT,
    shot_type VARCHAR(50),

    is_opponent TINYINT(1) DEFAULT 0,

    FOREIGN KEY (match_id) REFERENCES `match`(id),
    FOREIGN KEY (player_id) REFERENCES player(id)
);

-- ============================
-- LIVE BALL TABLE
-- ============================
CREATE TABLE IF NOT EXISTS live_ball (
    id INT AUTO_INCREMENT PRIMARY KEY,
    match_id INT,
    over_no INT,
    ball_no INT,

    striker INT,
    non_striker INT,
    bowler INT,

    runs INT DEFAULT 0,
    extras VARCHAR(50),
    wicket VARCHAR(50),

    commentary TEXT,
    angle FLOAT,
    shot_type VARCHAR(50),

    FOREIGN KEY (match_id) REFERENCES `match`(id)
);

-- ============================
-- PLAYER STATS TABLE
-- ============================
CREATE TABLE IF NOT EXISTS player_stats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    player_id INT,

    total_runs INT DEFAULT 0,
    balls_faced INT DEFAULT 0,
    fours INT DEFAULT 0,
    sixes INT DEFAULT 0,

    overs FLOAT DEFAULT 0,
    runs_conceded INT DEFAULT 0,
    wickets INT DEFAULT 0,

    catches INT DEFAULT 0,
    drops INT DEFAULT 0,
    saves INT DEFAULT 0,

    FOREIGN KEY (player_id) REFERENCES player(id)
);

-- =============================
-- INSERT 11 PLAYER USERS
-- =============================


-- =============================
-- INSERT 11 PLAYER USERS
-- =============================

INSERT INTO user (username, email, password_hash, role, status) VALUES
('player1', 'p1@example.com',  'test', 'player', 'approved'),
('player2', 'p2@example.com',  'test', 'player', 'approved'),
('player3', 'p3@example.com',  'test', 'player', 'approved'),
('player4', 'p4@example.com',  'test', 'player', 'approved'),
('player5', 'p5@example.com',  'test', 'player', 'approved'),
('player6', 'p6@example.com',  'test', 'player', 'approved'),
('player7', 'p7@example.com',  'test', 'player', 'approved'),
('player8', 'p8@example.com',  'test', 'player', 'approved'),
('player9', 'p9@example.com',  'test', 'player', 'approved'),
('player10', 'p10@example.com','test', 'player', 'approved'),
('player11', 'p11@example.com','test', 'player', 'approved');


-- =============================
-- INSERT PLAYER PROFILES
-- =============================

INSERT INTO player (user_id, batting_style, bowling_style, role_in_team, profile_completed)
VALUES
((SELECT id FROM user WHERE username='player1'),  'Right-Hand Bat', 'Right-Arm Medium', 'Batsman', 1),
((SELECT id FROM user WHERE username='player2'),  'Right-Hand Bat', 'Right-Arm Fast',  'Bowler', 1),
((SELECT id FROM user WHERE username='player3'),  'Left-Hand Bat',  'Left-Arm Spin',   'All-Rounder', 1),
((SELECT id FROM user WHERE username='player4'),  'Right-Hand Bat', 'Right-Arm Spin',  'Batsman', 1),
((SELECT id FROM user WHERE username='player5'),  'Right-Hand Bat', 'Right-Arm Medium','Wicket-Keeper', 1),
((SELECT id FROM user WHERE username='player6'),  'Left-Hand Bat',  'Left-Arm Fast',   'Bowler', 1),
((SELECT id FROM user WHERE username='player7'),  'Right-Hand Bat', 'Right-Arm Medium','Batsman', 1),
((SELECT id FROM user WHERE username='player8'),  'Right-Hand Bat', 'Right-Arm Medium','Bowler', 1),
((SELECT id FROM user WHERE username='player9'),  'Left-Hand Bat',  'Left-Arm Spin',   'Batsman', 1),
((SELECT id FROM user WHERE username='player10'), 'Right-Hand Bat', 'Right-Arm Fast',  'All-Rounder', 1),
((SELECT id FROM user WHERE username='player11'), 'Right-Hand Bat', 'Right-Arm Medium','Bowler', 1);
