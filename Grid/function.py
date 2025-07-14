from models.models import MarketingContent,TaskChecklistLink,Task,Checklist,TaskStatus, TaskType ,TaskUpdateLog, TaskTimeLog


def mark_content_completed(task_id: int, db, updated_by):
    content = db.query(MarketingContent).filter(MarketingContent.task_id == task_id,MarketingContent.is_delete==False).first()
    if content is None:
        return
    content.previous_status = content.status
    content.status = "Completed"
    db.commit()
    return content