from flask import session
from datetime import datetime


def detectar_cambios(actual, nuevo_dict, campos):
    cambios = {}
    for campo in campos:
        viejo = actual[campo]
        nuevo = nuevo_dict.get(campo)
        if viejo != nuevo:
            cambios[campo] = (viejo, nuevo)
    return cambios


def log_operation(
    db,
    project_id,
    user_id,
    action_type,
    instance_type,
    instance_id,
    instance_name,
    changes,
):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for field, (old, new) in changes.items():
        db.execute(
            """
            INSERT INTO project_operations_log (
                project_id, user_id, timestamp, action_type,
                instance_type, instance_id, instance_name,
                field_changed, old_value, new_value
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                project_id,
                user_id,
                timestamp,
                action_type,
                instance_type,
                instance_id,
                instance_name,
                field,
                old,
                new,
            ),
        )
    db.commit()
