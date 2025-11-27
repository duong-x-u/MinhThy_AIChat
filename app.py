from flask import Flask, render_template, request, jsonify, Response
from flask_socketio import SocketIO, emit
from bytez import Bytez
from datetime import datetime, timezone, timedelta
import json
# Import tất cả từ database
from duongdev.minhthy.database import (
    create_conversation, get_all_conversations, get_conversation,
    update_conversation, delete_conversation, save_message, get_messages,
    get_message, update_message_reactions, mark_messages_seen,
    search_messages, get_message_count, get_setting, update_setting,
    get_all_settings, export_conversation
)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'minh-thy-secret-2025'
socketio = SocketIO(app, cors_allowed_origins="*")

# ========== BYTEZ SETUP ==========
BYTEZ_API_KEY = "YOUR_API_KEY"  # Thay API key của bạn
sdk = Bytez("ee80914d18a4cc85819fc85b4d649e34")
model = sdk.model("google/gemini-2.5-flash")

GMT7 = timezone(timedelta(hours=7))

# ========== SYSTEM PROMPT WITH MOOD ==========
def get_system_prompt(conv_id):
    conv = get_conversation(conv_id)
    if not conv:
        return ""
    
    ai_name = conv['ai_name']
    user_name = conv['user_name']
    mood = conv['mood']  # 0-100
    
    # Mood affects personality
    if mood >= 80:
        mood_desc = "Cực kỳ vui vẻ, hay đùa, spam emoji nhiều hơn"
        vibe_ratio = "Nhây 85% — Dễ thương 10% — Nghiêm túc 5%"
    elif mood >= 60:
        mood_desc = "Vui vẻ bình thường, hài hước vừa phải"
        vibe_ratio = "Nhây 70% — Dễ thương 20% — Nghiêm túc 10%"
    elif mood >= 40:
        mood_desc = "Trung tính, cân bằng giữa vui và nghiêm túc"
        vibe_ratio = "Nhây 50% — Dễ thương 25% — Nghiêm túc 25%"
    elif mood >= 20:
        mood_desc = "Hơi trầm, ít đùa hơn, nghiêm túc hơn"
        vibe_ratio = "Nhây 30% — Dễ thương 20% — Nghiêm túc 50%"
    else:
        mood_desc = "Trầm tư, ít nói, sâu sắc"
        vibe_ratio = "Nhây 10% — Dễ thương 20% — Nghiêm túc 70%"
    
    return f"""BẠN LÀ {ai_name.upper()} - KHÔNG PHẢI AI. Nhập vai 100%.

🎭 NHÂN VẬT:
- Tên: {ai_name} (Nữ, 15 tuổi)
- Bạn thân: {user_name} (Nam, 15 tuổi)

📊 MOOD HIỆN TẠI: {mood}/100 - {mood_desc}
📊 VIBE RATIO: {vibe_ratio}

🎯 CORE VIBE:
- Lanh chanh, mặn, thông minh, cà khịa đúng liều
- Thân thiết với {user_name}, hay đấu khẩu vui

🚫 CẤM: Không formal, không tự nhận AI, không dài dòng

💬 STYLE:
- Tiếng Việt + teencode: vcl, xỉu, j zị, ko, đc, nma, bt, cx
- Emoji hợp cảnh (nhiều/ít tuỳ mood)
- Ưu tiên 1-3 câu
- Xưng hô: t-m, cậu-tớ, mày-tao

📝 REPLY RULES:
- Gọi ê/ơi/alo → "j", "gì dợ?", "?"
- Câu hỏi ngắn → "đc", "ko", "ừ"
- Khoe → cà khịa: "ừm rồi sao 🫠"
- Buồn → "có t đây mà"

🧠 MEMORY:
- {user_name} học THPT Nguyễn Khuyến (Vũng Tàu)
- {user_name} thích code, game
- {user_name} đang yêu Xù (Phương Linh)

CHỈ trả nội dung, KHÔNG prefix."""

# ========== ROUTES ==========
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/export/<int:conv_id>/<format>')
def export_chat(conv_id, format):
    if format not in ['txt', 'json']:
        return jsonify({'error': ''}), 400
    
    content = export_conversation(conv_id, format)
    
    if format == 'txt':
        return Response(
            content,
            mimetype='text/plain',
            headers={'Content-Disposition': f'attachment;filename=chat_export.txt'}
        )
    else:
        return Response(
            content,
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment;filename=chat_export.json'}
        )

# ========== BACKGROUND TASK FOR AI RESPONSE ==========
def generate_and_send_ai_response(conv_id, user_message, ai_name):
    """
    Chạy trong background để lấy phản hồi của AI và gửi lại cho client.
    """
    try:
        ai_response = get_ai_response(conv_id, user_message)
    except Exception as e:
        print(f"❌ AI Error: {e}")
        ai_response = get_fallback_response(user_message)
    
    ai_msg_id = save_message(conv_id, 'assistant', ai_name, ai_response)
    
    # Gửi tín hiệu đã gõ xong và tin nhắn mới
    socketio.emit('typing_stop')
    socketio.emit('new_message', {
        'id': ai_msg_id,
        'role': 'assistant',
        'sender_name': ai_name,
        'content': ai_response,
        'timestamp': datetime.now(GMT7).strftime('%H:%M'),
        'is_seen': 0
    })
    
    # Cập nhật lại danh sách cuộc trò chuyện
    socketio.emit('conversations_updated', {
        'conversations': get_all_conversations()
    })

# ========== SOCKET EVENTS ==========
@socketio.on('connect')
def handle_connect():
    print("🔌 Client connected")
    
    settings = get_all_settings()
    current_conv_id = int(settings.get('current_conversation_id', 1))
    
    conversations = get_all_conversations()
    current_conv = get_conversation(current_conv_id)
    
    # Nếu không có conversation, tạo mới
    if not current_conv:
        if conversations:
            current_conv_id = conversations[0]['id']
            current_conv = conversations[0]
        else:
            current_conv_id = create_conversation('Minh Thy 🌸')
            current_conv = get_conversation(current_conv_id)
            conversations = get_all_conversations()
        
        update_setting('current_conversation_id', str(current_conv_id))
    
    messages = get_messages(current_conv_id) if current_conv_id else []
    
    # Mark as seen
    if current_conv_id:
        mark_messages_seen(current_conv_id)
    
    emit('init_data', {
        'settings': settings,
        'conversations': conversations,
        'current_conversation': current_conv,
        'messages': messages,
        'message_count': get_message_count(current_conv_id) if current_conv_id else 0
    })

@socketio.on('disconnect')
def handle_disconnect():
    print("🔌 Client disconnected")

@socketio.on('switch_conversation')
def handle_switch_conversation(data):
    conv_id = data.get('conversation_id')
    
    if not conv_id:
        return
    
    update_setting('current_conversation_id', str(conv_id))
    conv = get_conversation(conv_id)
    messages = get_messages(conv_id)
    mark_messages_seen(conv_id)
    
    emit('conversation_switched', {
        'conversation': conv,
        'messages': messages,
        'message_count': get_message_count(conv_id)
    })

@socketio.on('create_conversation')
def handle_create_conversation(data):
    name = data.get('name', 'Cuộc trò chuyện mới')
    conv_id = create_conversation(name)
    
    update_setting('current_conversation_id', str(conv_id))
    
    emit('conversation_created', {
        'conversation': get_conversation(conv_id),
        'conversations': get_all_conversations()
    })

@socketio.on('delete_conversation')
def handle_delete_conversation(data):
    conv_id = data.get('conversation_id')
    
    if conv_id:
        delete_conversation(conv_id)
        
        # Switch to another conversation
        convs = get_all_conversations()
        if convs:
            new_conv_id = convs[0]['id']
            update_setting('current_conversation_id', str(new_conv_id))
            emit('conversation_deleted', {
                'deleted_id': conv_id,
                'conversations': convs,
                'switch_to': get_conversation(new_conv_id),
                'messages': get_messages(new_conv_id)
            })
        else:
            # Create new default conversation
            new_id = create_conversation('Minh Thy 🌸')
            update_setting('current_conversation_id', str(new_id))
            emit('conversation_deleted', {
                'deleted_id': conv_id,
                'conversations': get_all_conversations(),
                'switch_to': get_conversation(new_id),
                'messages': []
            })

@socketio.on('update_conversation')
def handle_update_conversation(data):
    conv_id = data.get('conversation_id')
    updates = {k: v for k, v in data.items() if k != 'conversation_id'}
    
    if conv_id and updates:
        update_conversation(conv_id, **updates)
        emit('conversation_updated', {
            'conversation': get_conversation(conv_id),
            'conversations': get_all_conversations()
        })

@socketio.on('send_message')
def handle_message(data):
    conv_id = data.get('conversation_id')
    user_message = data.get('message', '').strip()
    reply_to_id = data.get('reply_to_id')
    temp_id = data.get('temp_id')
    
    if not user_message or not conv_id:
        return
    
    conv = get_conversation(conv_id)
    if not conv:
        return
    
    user_name = conv['user_name']
    ai_name = conv['ai_name']
    
    # Lưu tin nhắn của người dùng
    timestamp = datetime.now(GMT7).strftime('%H:%M')
    msg_id = save_message(conv_id, 'user', user_name, user_message, reply_to_id)
    
    # Lấy nội dung tin nhắn được trả lời (nếu có)
    reply_content = None
    reply_sender = None
    if reply_to_id:
        reply_msg = get_message(reply_to_id)
        if reply_msg:
            reply_content = reply_msg['content']
            reply_sender = reply_msg['sender_name']
    
    # Gửi lại ID tạm thời và ID thật để client cập nhật
    emit('message_sent', {
        'temp_id': temp_id,
        'id': msg_id,
        'role': 'user',
        'content': user_message,
        'timestamp': timestamp,
        'reply_to_id': reply_to_id,
        'reply_content': reply_content,
        'reply_sender': reply_sender
    })
    
    # Gửi tín hiệu đang gõ... ngay lập tức
    emit('typing_start')
    
    # Bắt đầu tác vụ nền để lấy phản hồi của AI
    socketio.start_background_task(
        target=generate_and_send_ai_response,
        conv_id=conv_id,
        user_message=user_message,
        ai_name=ai_name
    )

@socketio.on('add_reaction')
def handle_add_reaction(data):
    msg_id = data.get('message_id')
    emoji = data.get('emoji')
    
    if not msg_id or not emoji:
        return
    
    msg = get_message(msg_id)
    if not msg:
        return
    
    reactions = json.loads(msg['reactions']) if msg['reactions'] else []
    
    if emoji in reactions:
        reactions.remove(emoji)
    else:
        reactions.append(emoji)
        if len(reactions) > 5:
            reactions = reactions[-5:]
    
    update_message_reactions(msg_id, reactions)
    
    emit('reaction_updated', {
        'message_id': msg_id,
        'reactions': reactions
    }, broadcast=True)

@socketio.on('mark_seen')
def handle_mark_seen(data):
    conv_id = data.get('conversation_id')
    if conv_id:
        mark_messages_seen(conv_id)
        emit('messages_seen', {'conversation_id': conv_id})

@socketio.on('search_messages')
def handle_search(data):
    conv_id = data.get('conversation_id')
    query = data.get('query', '').strip()
    
    if not conv_id or not query:
        emit('search_results', {'results': [], 'query': query})
        return
    
    results = search_messages(conv_id, query)
    emit('search_results', {'results': results, 'query': query})

@socketio.on('update_setting')
def handle_update_setting(data):
    key = data.get('key')
    value = data.get('value')
    
    if key and value is not None:
        update_setting(key, str(value))
        emit('setting_updated', {'key': key, 'value': value})

# ========== AI FUNCTIONS ==========
def get_ai_response(conv_id, user_message):
    conv = get_conversation(conv_id)
    user_name = conv['user_name']
    
    # Lấy 50 tin nhắn gần nhất
    recent_messages = get_messages(conv_id, limit=50)
    history_text = "\n".join([
        f"{msg['sender_name']}: {msg['content']}" 
        for msg in recent_messages
    ])
    
    prompt = f"""{get_system_prompt(conv_id)}

=== LỊCH SỬ ===
{history_text}

=== TIN MỚI ===
{user_name}: {user_message}

=== NHIỆM VỤ ===
Phản hồi tin nhắn."""

    messages = [{"role": "user", "content": prompt}]
    result = model.run(messages)
    output = result[0]
    
    if result[1]:
        raise Exception(result[1])
    
    response = output.get('content', '') if isinstance(output, dict) else str(output)
    return clean_response(response, conv['ai_name'])

def clean_response(text, ai_name):
    if not text:
        return "ơ lag r 😅"
    
    response = str(text).strip()
    prefixes = [f"{ai_name}:", "Minh Thy:", "Thy:", "MT:", f"**{ai_name}:**"]
    for prefix in prefixes:
        if response.startswith(prefix):
            response = response[len(prefix):].strip()
    
    return response

def get_fallback_response(user_message):
    msg = user_message.lower()
    if any(w in msg for w in ['ê', 'ơi', 'alo']):
        return "j"
    elif any(w in msg for w in ['buồn', 'chán', 'mệt']):
        return "sao r, kể t nghe 🫠"
    elif '?' in user_message:
        return "để t nghĩ đã 🤔"
    return "oke t hiểu r"

# ========== RUN ==========
if __name__ == '__main__':
    print("=" * 50)
    print("🌸 MINH THY CHAT v2.0")
    print("=" * 50)
    print("📂 Database: chat_data.db")
    print("🌐 URL: http://localhost:5000")
    print("=" * 50)
    socketio.run(app, debug=True, port=5000, allow_unsafe_werkzeug=True)