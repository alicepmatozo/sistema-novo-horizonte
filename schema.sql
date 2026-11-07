CREATE DATABASE IF NOT EXISTS novo_horizonte DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE novo_horizonte;

-- Tabela de Unidades
CREATE TABLE IF NOT EXISTS unidades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL UNIQUE,
    ativa BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Usuários Administrativos
CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    usuario VARCHAR(50) NOT NULL UNIQUE,
    senha_hash VARCHAR(255) NOT NULL,
    cargo VARCHAR(50) DEFAULT 'Administrador',
    bloqueado BOOLEAN DEFAULT FALSE,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Solicitações
CREATE TABLE IF NOT EXISTS solicitacoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    protocolo VARCHAR(20) NOT NULL UNIQUE,
    unidade_id INT NOT NULL,
    unidade_nome VARCHAR(100) NOT NULL, -- Preserva histórico se unidade mudar de nome
    responsavel VARCHAR(100) NOT NULL,
    data_solicitacao DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status ENUM('Pendente', 'Em análise', 'Aprovada', 'Em separação', 'Atendida', 'Recusada') DEFAULT 'Pendente',
    observacoes_gerais TEXT,
    observacoes_admin TEXT,
    FOREIGN KEY (unidade_id) REFERENCES unidades(id)
);

-- Tabela de Itens da Solicitação
CREATE TABLE IF NOT EXISTS solicitacao_itens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    solicitacao_id INT NOT NULL,
    categoria VARCHAR(50) NOT NULL,
    produto VARCHAR(100) NOT NULL,
    quantidade DECIMAL(10,2) NOT NULL,
    unidade_medida VARCHAR(20) NOT NULL,
    observacao VARCHAR(255),
    FOREIGN KEY (solicitacao_id) REFERENCES solicitacoes(id) ON DELETE CASCADE
);

-- Tabela de Histórico e Auditoria
CREATE TABLE IF NOT EXISTS historico_alteracoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    solicitacao_id INT NOT NULL,
    usuario VARCHAR(100) NOT NULL,
    acao VARCHAR(100) NOT NULL,
    status_anterior VARCHAR(50),
    status_novo VARCHAR(50),
    observacao TEXT,
    data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (solicitacao_id) REFERENCES solicitacoes(id) ON DELETE CASCADE
);

-- Dados Iniciais (Unidades padrão e Usuário Admin)
INSERT IGNORE INTO unidades (id, nome) VALUES 
(1, 'Unidade 1 - Central'),
(2, 'Unidade 2 - Casa Lar'),
(3, 'Unidade 3 - Centro Dia');

-- Usuário Admin Inicial (Senha padrão: admin123)
-- Hash em Werkzeug/pbkdf2:sha256
INSERT IGNORE INTO usuarios (id, nome, usuario, senha_hash, cargo) VALUES 
(1, 'Administrador Geral', 'admin', 'pbkdf2:sha256:600000$g43XwN4K$839df5bd6d812354c4bd0c9d7a22bc74338d3ad48e9fbf3b3a697669d7b42021', 'Administrador');