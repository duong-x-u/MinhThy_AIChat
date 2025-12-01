import sqlite3
from datetime import datetime, timezone, timedelta
import json

DB_FILE = "chat_data.db"
GMT7 = timezone(timedelta(hours=7))

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def get_gmt7_now():
    """Lấy thời gian hiện tại GMT+7 dạng ISO"""
    return datetime.now(GMT7).strftime('%Y-%m-%d %H:%M:%S')

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Kích hoạt foreign keys
    cursor.execute("PRAGMA foreign_keys = ON")

    # Table conversations
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL DEFAULT 'Cuộc trò chuyện mới',
            ai_name TEXT DEFAULT 'Minh Thy',
            user_name TEXT DEFAULT 'Dương',
            mood INTEGER DEFAULT 70,
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    # Thêm cột ai_presence_status nếu chưa tồn tại
    cursor.execute("PRAGMA table_info(conversations)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'ai_presence_status' not in columns:
        cursor.execute("ALTER TABLE conversations ADD COLUMN ai_presence_status TEXT DEFAULT 'online'")
    
    # Table messages
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            sender_name TEXT NOT NULL,
            content TEXT NOT NULL,
            reply_to_id INTEGER DEFAULT NULL,
            reactions TEXT DEFAULT '[]',
            is_seen INTEGER DEFAULT 0,
            timestamp TEXT,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
            FOREIGN KEY (reply_to_id) REFERENCES messages(id) ON DELETE SET NULL
        )
    ''')
    
    # Table memories
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            fact TEXT NOT NULL,
            created_at TEXT,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        )
    ''')

    # Table settings
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')
    
    # Default settings
    cursor.execute('''
        INSERT OR IGNORE INTO settings (key, value) VALUES 
        ('theme', 'dark'),
        ('sound_enabled', 'true'),
        ('current_conversation_id', '1')
    ''')
    
    # Create default conversation if none exists
    cursor.execute('SELECT COUNT(*) as count FROM conversations')
    if cursor.fetchone()['count'] == 0:
        now = get_gmt7_now()
        cursor.execute('''
            INSERT INTO conversations (name, ai_name, user_name, mood, created_at, updated_at) 
            VALUES ('Minh Thy 🌸', 'Minh Thy', 'Dương', 70, ?, ?)
        ''', (now, now))
        # Thêm ký ức mặc định
        cursor.execute('''
            INSERT INTO memories (conversation_id, fact, created_at) VALUES
            (1, 'học THPT Nguyễn Khuyến (Vũng Tàu)', ?),
            (1, 'thích code, game', ?),
            (1, 'đang yêu Xù (Phương Linh)', ?)
        ''', (now, now, now))

    conn.commit()
    conn.close()

# ========== CONVERSATIONS ==========
def create_conversation(name="Cuộc trò chuyện mới", ai_name="Minh Thy", user_name="Dương"):
    conn = get_db()
    cursor = conn.cursor()
    now = get_gmt7_now()
    cursor.execute(
        '''INSERT INTO conversations (name, ai_name, user_name, created_at, updated_at) 
           VALUES (?, ?, ?, ?, ?)''',
        (name, ai_name, user_name, now, now)
    )
    conn.commit()
    conv_id = cursor.lastrowid
    conn.close()
    return conv_id

def get_all_conversations():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.*, 
               (SELECT content FROM messages WHERE conversation_id = c.id ORDER BY timestamp DESC LIMIT 1) as last_message,
               (SELECT timestamp FROM messages WHERE conversation_id = c.id ORDER BY timestamp DESC LIMIT 1) as last_message_time,
               (SELECT role FROM messages WHERE conversation_id = c.id ORDER BY timestamp DESC LIMIT 1) as last_sender_role,
               (SELECT COUNT(*) FROM messages WHERE conversation_id = c.id) as message_count
        FROM conversations c 
        ORDER BY c.updated_at DESC
    ''')
    convs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return convs

def get_conversation(conv_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM conversations WHERE id = ?', (conv_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_conversation(conv_id, **kwargs):
    conn = get_db()
    cursor = conn.cursor()
    
    allowed_fields = ['name', 'ai_name', 'user_name', 'mood', 'ai_presence_status']
    updates = []
    values = []
    
    for key, value in kwargs.items():
        if key in allowed_fields:
            updates.append(f'{key} = ?')
            values.append(value)
    
    if updates:
        updates.append('updated_at = ?')
        values.append(get_gmt7_now())
        values.append(conv_id)
        cursor.execute(
            f'UPDATE conversations SET {", ".join(updates)} WHERE id = ?',
            values
        )
        conn.commit()
    conn.close()

def update_conversation_presence(conv_id, status):
    conn = get_db()
    cursor = conn.cursor()
    now = get_gmt7_now()
    cursor.execute(
        'UPDATE conversations SET ai_presence_status = ?, updated_at = ? WHERE id = ?',
        (status, now, conv_id)
    )
    conn.commit()
    conn.close()

def delete_conversation(conv_id):
    conn = get_db()
    cursor = conn.cursor()
    # Foreign key "ON DELETE CASCADE" sẽ tự động xóa messages và memories
    cursor.execute('DELETE FROM conversations WHERE id = ?', (conv_id,))
    conn.commit()
    conn.close()

# ========== MESSAGES ==========
def save_message(conversation_id, role, sender_name, content, reply_to_id=None):
    conn = get_db()
    cursor = conn.cursor()
    now = get_gmt7_now()
    
    # Update conversation timestamp
    cursor.execute(
        'UPDATE conversations SET updated_at = ? WHERE id = ?',
        (now, conversation_id)
    )
    
    cursor.execute(
        '''INSERT INTO messages (conversation_id, role, sender_name, content, reply_to_id, timestamp) 
           VALUES (?, ?, ?, ?, ?, ?)''',
        (conversation_id, role, sender_name, content, reply_to_id, now)
    )
    conn.commit()
    msg_id = cursor.lastrowid
    conn.close()
    return msg_id

def get_messages(conversation_id, limit=None):
    conn = get_db()
    cursor = conn.cursor()
    
    if limit:
        cursor.execute('''
            SELECT * FROM (
                SELECT m.*, 
                       r.content as reply_content,
                       r.sender_name as reply_sender
                FROM messages m
                LEFT JOIN messages r ON m.reply_to_id = r.id
                WHERE m.conversation_id = ?
                ORDER BY m.timestamp DESC 
                LIMIT ?
            ) sub ORDER BY timestamp ASC
        ''', (conversation_id, limit))
    else:
        cursor.execute('''
            SELECT m.*, 
                   r.content as reply_content,
                   r.sender_name as reply_sender
            FROM messages m
            LEFT JOIN messages r ON m.reply_to_id = r.id
            WHERE m.conversation_id = ?
            ORDER BY m.timestamp ASC
        ''', (conversation_id,))
    
    messages = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return messages

def get_message(msg_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM messages WHERE id = ?', (msg_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_message_reactions(msg_id, reactions):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE messages SET reactions = ? WHERE id = ?',
        (json.dumps(reactions), msg_id)
    )
    conn.commit()
    conn.close()

def mark_messages_seen(conversation_id, role='assistant'):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE messages SET is_seen = 1 WHERE conversation_id = ? AND role = ?',
        (conversation_id, role)
    )
    conn.commit()
    conn.close()

def search_messages(conversation_id, query):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        '''SELECT * FROM messages 
           WHERE conversation_id = ? AND content LIKE ? 
           ORDER BY timestamp DESC LIMIT 50''',
        (conversation_id, f'%{query}%')
    )
    messages = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return messages

def get_message_count(conversation_id=None):
    conn = get_db()
    cursor = conn.cursor()
    if conversation_id:
        cursor.execute('SELECT COUNT(*) as count FROM messages WHERE conversation_id = ?', (conversation_id,))
    else:
        cursor.execute('SELECT COUNT(*) as count FROM messages')
    count = cursor.fetchone()['count']
    conn.close()
    return count

# ========== MEMORIES ==========
def get_memories(conversation_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM memories WHERE conversation_id = ? ORDER BY created_at ASC', (conversation_id,))
    memories = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return memories

def add_memory(conversation_id, fact):
    conn = get_db()
    cursor = conn.cursor()
    now = get_gmt7_now()
    cursor.execute(
        'INSERT INTO memories (conversation_id, fact, created_at) VALUES (?, ?, ?)',
        (conversation_id, fact, now)
    )
    conn.commit()
    memory_id = cursor.lastrowid
    conn.close()
    return memory_id

def delete_memory(memory_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM memories WHERE id = ?', (memory_id,))
    conn.commit()
    conn.close()

# ========== SETTINGS ==========
def get_setting(key):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
    row = cursor.fetchone()
    conn.close()
    return row['value'] if row else None

def update_setting(key, value):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()

def get_all_settings():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM settings')
    settings = {row['key']: row['value'] for row in cursor.fetchall()}
    conn.close()
    return settings

# ========== EXPORT ==========
def export_conversation(conversation_id, format='txt'):
    conv = get_conversation(conversation_id)
    messages = get_messages(conversation_id)
    
    if format == 'txt':
        lines = [f"=== {conv['name']} ===\n"]
        lines.append(f"AI: {conv['ai_name']} | User: {conv['user_name']}\n")
        lines.append("=" * 40 + "\n\n")
        for msg in messages:
            time = msg['timestamp'] or ''
            lines.append(f"[{time}] {msg['sender_name']}:\n{msg['content']}\n\n")
        return ''.join(lines)
    
    elif format == 'json':
        return json.dumps({
            'conversation': conv,
            'messages': messages
        }, ensure_ascii=False, indent=2)
    
    return None

# Initialize
init_db()