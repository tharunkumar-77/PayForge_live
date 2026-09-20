from app.models.audit import AuditLog

def log_audit(db,event,transaction_id=None,details=None):
    entry = AuditLog(event=event, transaction_id=transaction_id, details=details)
    db.add(entry)
    return entry