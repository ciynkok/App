-- Task Schema Initialization
-- Схема для сервиса задач

CREATE SCHEMA IF NOT EXISTS task;

-- Доски
CREATE TABLE IF NOT EXISTS task.boards (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title       VARCHAR(255) NOT NULL,
    description TEXT,
    owner_id    UUID NOT NULL,
    color       VARCHAR(7) DEFAULT '#6366f1',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Участники досок
CREATE TABLE IF NOT EXISTS task.board_members (
    board_id    UUID NOT NULL REFERENCES task.boards(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL,
    role        VARCHAR(20) NOT NULL DEFAULT 'viewer'
                CHECK (role IN ('admin', 'editor', 'viewer')),
    PRIMARY KEY (board_id, user_id)
);

-- Колонки (списки Kanban)
CREATE TABLE IF NOT EXISTS task.columns (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    board_id    UUID NOT NULL REFERENCES task.boards(id) ON DELETE CASCADE,
    title       VARCHAR(255) NOT NULL,
    position    INT NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Задачи
CREATE TABLE IF NOT EXISTS task.tasks (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    column_id   UUID NOT NULL REFERENCES task.columns(id) ON DELETE CASCADE,
    board_id    UUID NOT NULL REFERENCES task.boards(id) ON DELETE CASCADE,
    title       VARCHAR(255) NOT NULL,
    description TEXT,
    assignee_id UUID,
    priority    VARCHAR(10) DEFAULT 'medium'
                CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
    status      VARCHAR(20) DEFAULT 'todo',
    deadline    TIMESTAMPTZ,
    position    INT NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS tasks_board_id_idx ON task.tasks(board_id);
CREATE INDEX IF NOT EXISTS tasks_column_id_idx ON task.tasks(column_id);
CREATE INDEX IF NOT EXISTS tasks_assignee_id_idx ON task.tasks(assignee_id);

-- Комментарии
CREATE TABLE IF NOT EXISTS task.comments (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id     UUID NOT NULL REFERENCES task.tasks(id) ON DELETE CASCADE,
    author_id   UUID NOT NULL,
    content     TEXT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS comments_task_id_idx ON task.comments(task_id);
