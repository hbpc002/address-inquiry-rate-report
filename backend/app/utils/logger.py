from app.models.operation_log import OperationLog


def log_operation(db, user_id, operation_type, target_table, target_id=None, details=None):
    """记录操作日志"""
    log = OperationLog(
        user_id=user_id,
        operation_type=operation_type,
        target_table=target_table,
        target_id=target_id,
        details=details
    )
    db.add(log)
    db.commit()