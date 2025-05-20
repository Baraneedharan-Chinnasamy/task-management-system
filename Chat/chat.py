from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
from models.models import ChatMessage, ChatRoom, ChatMessageRead,Task,TaskType,User
from database.database import get_db, SessionLocal
from Chat.chat_manager import ChatManager
from fastapi import Query

def get_original_normal_task(db: Session, task_id: int):
    current_task = db.query(Task).filter(Task.task_id == task_id).first()
    if not current_task:
        return None

    # Traverse up the parent chain until you reach a Normal task
    while current_task.task_type == TaskType.Review and current_task.parent_task_id:
        parent = db.query(Task).filter(Task.task_id == current_task.parent_task_id).first()
        if not parent:
            break
        current_task = parent

    return current_task

router = APIRouter()
chat_manager = ChatManager()


@router.websocket("/chat")
async def chat_websocket(
    websocket: WebSocket,
    task_id: int = Query(...),
    user_id: int = Query(...),
    db: Session = Depends(get_db)
):
    print(f"🌐 WebSocket connection request received | task_id={task_id}, user_id={user_id}")

    try:
        task = db.query(Task).filter(Task.task_id == task_id).first()
        if not task:
            print("❌ Task not found!")
            return  # FastAPI will respond with 403

        if task.task_type == TaskType.Review:
            original_task = get_original_normal_task(db, task_id)
            if not original_task:
                print("❌ Original task not found!")
                return
            task_ids = original_task.task_id
        else:
            task_ids = task.task_id
        print(f"📌 Final task ID: {task_ids}")

        chat_room = db.query(ChatRoom).filter(ChatRoom.task_id == task_ids).first()
        if not chat_room:
            print("❌ Chat room not found!")
            return  # 403 rejection

        chat_room_id = chat_room.chat_room_id
        print(f"💬 Chat room ID: {chat_room_id}")

        await websocket.accept()
        print("✅ WebSocket connection accepted")

        websocket.scope["user_id"] = user_id
        await chat_manager.connect(websocket, chat_room_id)
        print("🔗 User connected to chat room")

        users = db.query(User).all()
        user_map = {u.employee_id: u.username for u in users}
        print(f"👥 Loaded {len(users)} users")

        while True:
            data = await websocket.receive_json()
            print(f"📨 Received message: {data}")

            message_text = data.get("message")
            sender_id = data.get("sender_id")
            visible_to = data.get("visible_to")

            chat_message = ChatMessage(
                chat_room_id=chat_room_id,
                sender_id=sender_id,
                message=message_text,
                visible_to=visible_to
            )
            db.add(chat_message)
            db.commit()
            db.refresh(chat_message)
            print(f"💾 Message saved to DB (ID: {chat_message.message_id})")

            message_payload = {
                "message_id": chat_message.message_id,
                "sender_id": sender_id,
                "sender_name": user_map.get(sender_id),
                "message": message_text,
                "visible_to": visible_to,
                "timestamp": chat_message.timestamp.isoformat()
            }

            if not visible_to:
                await chat_manager.broadcast(chat_room_id, message_payload, db=db)
                print("📡 Broadcast to all users")
            else:
                await chat_manager.broadcast_to_users(chat_room_id, message_payload, visible_to, db=db)
                print(f"📡 Broadcast to users: {visible_to}")

    except WebSocketDisconnect:
        print("🔌 WebSocket disconnected")
        chat_manager.disconnect(websocket, chat_room_id)
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        chat_manager.disconnect(websocket, chat_room_id)
    finally:
        db.close()
        print("🔚 Database session closed")


@router.get("/chat_history")
def get_chat_history(
    task_id: int,
    user_id: int,
    page: int = 1,
    limit: int = 30,
    before_timestamp: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    if page < 1:
        raise HTTPException(status_code=400, detail="Page number must be >= 1")

    # Build user map
    users = db.query(User).all()
    user_map = {u.employee_id: u.username for u in users}

    # Get task and related chat room
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.task_type == TaskType.Review:
        original_task = get_original_normal_task(db, task_id)
        task_ids = original_task.task_id
    else:
        task_ids = task.task_id

    chat_room = db.query(ChatRoom).filter(ChatRoom.task_id == task_ids).first()
    if not chat_room:
        raise HTTPException(status_code=404, detail="Chat room not found")

    chat_room_id = chat_room.chat_room_id

    # Build query
    query = db.query(ChatMessage).filter(ChatMessage.chat_room_id == chat_room_id)
    if before_timestamp:
        query = query.filter(ChatMessage.timestamp < before_timestamp)

    offset = (page - 1) * limit
    fetched_messages = query.order_by(ChatMessage.timestamp.desc()).offset(offset).limit(limit + 1).all()

    has_more = len(fetched_messages) > limit
    messages = fetched_messages[:limit]
    messages.reverse()

    read_message_ids = {
        r.message_id for r in db.query(ChatMessageRead.message_id)
        .filter_by(user_id=user_id).all()
    }

    visible_messages = []
    for msg in messages:
        if not msg.visible_to or user_id in msg.visible_to:
            visible_messages.append({
                "message_id": msg.message_id,
                "sender_id": msg.sender_id,
                "sender_name": user_map.get(msg.sender_id),
                "message": msg.message,
                "timestamp": msg.timestamp.isoformat(),
                "seen": msg.message_id in read_message_ids
            })

            if msg.message_id not in read_message_ids and msg.sender_id != user_id:
                db.add(ChatMessageRead(message_id=msg.message_id, user_id=user_id))

    db.commit()

    return {
        "messages": visible_messages,
        "has_more": has_more,
        "page": page,
        "limit": limit
    }
