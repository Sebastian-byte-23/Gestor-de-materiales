from flask import Blueprint, request, jsonify, current_app, session
import json
import uuid
from .data_retrieval import get_db
from datetime import datetime
from flask import session
import pytz

# Create the Blueprint object
instances_bp = Blueprint("instances", __name__, url_prefix="/projects/instances")


@instances_bp.route("/create_instance", methods=["POST"])
def create_instance():
        data = request.json
        current_app.logger.debug(f"Create instance request data: {data}")
        db = get_db()

        try:
            # Handle accessory instance creation with application context
            if data["item_type"] == "accessory":
                # Check for existing instance with matching criteria
                instance = db.execute(
                    """
                    SELECT accessory_instance_id 
                    FROM Accessory_Instance
                    WHERE project_id = ? AND accessory_id = ?
                """,
                    (data["project_id"], data["item_id"]),
                ).fetchone()

                if not instance:
                    # Create new accessory instance
                    cursor = db.execute(
                        """
                        INSERT INTO Accessory_Instance (
                            project_id, accessory_id, name, short_name, 
                            description, short_description, installation
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            data["project_id"],
                            data["item_id"],
                            data["name"],
                            data["short_name"],
                            data["description"],
                            data["short_description"],
                            data["installation"],
                        ),
                    )
                    instance_id = cursor.lastrowid
                else:
                    instance_id = instance["accessory_instance_id"]

                # Create attributes with application context and group_id
                application = data.get("application", "")
                # Use existing group_id or generate a simple one
                group_id = data.get("group_id", f"group_{datetime.now().timestamp()}")
                # Remove any 'new_group_' prefix if present
                group_id = group_id.replace('new_group_', '')

                for name, value in data["attributes"].items():
                    db.execute(
                        """
                        INSERT INTO Accessory_Instance_Attributes (
                            accessory_instance_id, name, value, application, group_id
                        ) VALUES (?, ?, ?, ?, ?)
                    """,
                        (instance_id, name, json.dumps([value]), application, group_id),
                    )

                db.commit()
                log_operation(
                    db=db,
                    project_id=data["project_id"],
                    user_id=session.get("user_id"),
                    action_type="create",
                    instance_type=data["item_type"],
                    instance_id=instance_id,
                    instance_name=data["name"],
                    changes={
                        "name": (None, data["name"]),
                        "short_name": (None, data["short_name"]),
                        "description": (None, data["description"]),
                        "short_description": (None, data["short_description"]),
                        "installation": (None, data["installation"]),
                        **{
                            f"attr:{k}": (None, v)
                            for k, v in data["attributes"].items()
                        },
                    },
                )
                return jsonify({"success": True, "instance_id": instance_id})
            # Otherwise create a new item instance
            # Otherwise create a new item instance
            elif data["item_type"] == "window":
                cursor = db.execute(
                    """
                    INSERT INTO Windows (
                        project_id, name, total_height, total_width, bottom_height,
                        left_width, window_type, category_id, pane_states, finish, profile
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        data["project_id"],
                        data["name"],
                        data["total_height"],
                        data["total_width"],
                        data["bottom_height"],
                        data["left_width"],
                        data["window_type"],
                        data["category_id"],
                        json.dumps(data.get("pane_states", {})),
                        data["finish"],
                        data["profile"],
                    ),
                )
                instance_id = cursor.lastrowid
                db.commit()
                log_operation(
                    db=db,
                    project_id=data["project_id"],
                    user_id=session.get("user_id"),
                    action_type="create",
                    instance_type=data["item_type"],
                    instance_id=instance_id,
                    instance_name=data["name"],
                    changes={
                        "name": (None, data["name"]),
                        "short_name": (None, data["short_name"]),
                        "description": (None, data["description"]),
                        "short_description": (None, data["short_description"]),
                        "installation": (None, data["installation"]),
                        **{
                            f"attr:{k}": (None, v)
                            for k, v in data["attributes"].items()
                        },
                    },
                )
                return jsonify({"success": True, "instance_id": instance_id})

            elif data["item_type"] == "item":
                cursor = db.execute(
                    """
                    INSERT INTO Item_Instances (
                        project_id, item_id, name, short_name, description, 
                        short_description, installation
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        data["project_id"],
                        data["item_id"],
                        data["name"],
                        data["short_name"],
                        data["description"],
                        data["short_description"],
                        data["installation"],
                    ),
                )

                instance_id = cursor.lastrowid

                # Create attributes
                for name, value in data["attributes"].items():
                    db.execute(
                        """
                        INSERT INTO Item_Instance_Attributes (
                            instance_id, name, value
                        ) VALUES (?, ?, ?)
                    """,
                        (instance_id, name, json.dumps([value])),
                    )

                db.commit()
                log_operation(
                    db=db,
                    project_id=data["project_id"],
                    user_id=session.get("user_id"),
                    action_type="create",
                    instance_type=data["item_type"],
                    instance_id=instance_id,
                    instance_name=data["name"],
                    changes={
                        "name": (None, data["name"]),
                        "short_name": (None, data["short_name"]),
                        "description": (None, data["description"]),
                        "short_description": (None, data["short_description"]),
                        "installation": (None, data["installation"]),
                        **{
                            f"attr:{k}": (None, v)
                            for k, v in data["attributes"].items()
                        },
                    },
                )
                return jsonify({"success": True, "instance_id": instance_id})
        except Exception as e:
            db.rollback()
            return jsonify({"success": False, "error": str(e)})


# -------------------------------
# FUNCIONES AUXILIARES DE LOG
# -------------------------------


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

    chile_tz = pytz.timezone("America/Santiago")
    timestamp = datetime.now(chile_tz).strftime("%Y-%m-%d %H:%M:%S")
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


@instances_bp.route('/delete_instance', methods=['DELETE'])
def delete_instance():
        data = request.json
        current_app.logger.debug(f"Delete instance  {data}")  # Log the incoming data
        db = get_db()
        
        try:
            if data['instance_type'] == 'item':
                # Find accessory instances that reference this item instance
                accessory_instances = db.execute('''
                    SELECT DISTINCT ai.accessory_instance_id, ai.project_id
                    FROM Accessory_Instance ai
                    JOIN Accessory_Instance_Attributes aia ON ai.accessory_instance_id = aia.accessory_instance_id
                    WHERE aia.application = ?
                ''', (str(data['instance_id']),)).fetchall()
                current_app.logger.debug(f"Found accessory instances: {accessory_instances}")
                
                # For each accessory instance, check if this is the only application
                for acc in accessory_instances:
                    # Count applications for this accessory
                    app_count = db.execute('''
                        SELECT COUNT(DISTINCT application) as count
                        FROM Accessory_Instance_Attributes
                        WHERE accessory_instance_id = ? AND application IS NOT NULL AND application != ''
                    ''', (acc['accessory_instance_id'],)).fetchone()['count']
                    current_app.logger.debug(f"Accessory instance {acc['accessory_instance_id']} has {app_count} applications")

                    if app_count <= 1:
                        # This is the only application, delete the entire accessory instance
                        current_app.logger.debug(f"Deleting accessory instance {acc['accessory_instance_id']}")
                        db.execute('DELETE FROM Accessory_Instance_Attributes WHERE accessory_instance_id = ?', 
                                  (acc['accessory_instance_id'],))
                        db.execute('DELETE FROM Accessory_Instance WHERE accessory_instance_id = ? AND project_id = ?', 
                                  (acc['accessory_instance_id'], acc['project_id']))
                    else:
                        # Multiple applications exist, only delete attributes for this application
                        current_app.logger.debug(f"Deleting attributes for application {data['instance_id']} from accessory instance {acc['accessory_instance_id']}")
                        db.execute('DELETE FROM Accessory_Instance_Attributes WHERE accessory_instance_id = ? AND application = ?', 
                                  (acc['accessory_instance_id'], str(data['instance_id'])))
                
                # Delete item instance attributes (foreign key constraint)
                current_app.logger.debug(f"Deleting attributes for item instance {data['instance_id']}")
                db.execute('DELETE FROM Item_Instance_Attributes WHERE instance_id = ?', 
                          (data['instance_id'],))
                
                # Then delete the item instance
                current_app.logger.debug(f"Deleting item instance {data['instance_id']}")
                db.execute('DELETE FROM Item_Instances WHERE instance_id = ? AND project_id = ?', 
                          (data['instance_id'], data['project_id']))
            else:
                # Delete accessory instance attributes first (foreign key constraint)
                current_app.logger.debug(f"Deleting attributes for accessory instance {data['instance_id']}")
                db.execute('DELETE FROM Accessory_Instance_Attributes WHERE accessory_instance_id = ?', 
                          (data['instance_id'],))
                
                # Then delete the accessory instance
                current_app.logger.debug(f"Deleting accessory instance {data['instance_id']}")
                db.execute('DELETE FROM Accessory_Instance WHERE accessory_instance_id = ? AND project_id = ?', 
                          (data['instance_id'], data['project_id']))
            
            db.commit()
            current_app.logger.debug("Deletion successful")
            return jsonify({'success': True})
        except Exception as e:
            db.rollback()
            current_app.logger.error(f"Error during deletion: {e}")  # Log the error
            return jsonify({'success': False, 'error': str(e)})

@instances_bp.route('/delete_attribute_row', methods=['DELETE'])
def delete_attribute_row():
        data = request.json
        db = get_db()
        
        try:
            if data['instance_type'] == 'item':
                # For item instances, we don't have application-specific attributes
                # This is a safeguard, but the UI shouldn't allow this for items
                return jsonify({'success': False, 'error': 'Cannot delete application-specific attributes for items'})
            else:
                # Check if we have a group_id (preferred method)
                if data.get('group_id'):
                    # Delete all attributes with this group_id
                    db.execute('''
                        DELETE FROM Accessory_Instance_Attributes 
                        WHERE accessory_instance_id = ? AND group_id = ?
                    ''', (data['instance_id'], data['group_id']))
                # For backward compatibility, also handle application-based deletion
                elif data.get('application'):
                    db.execute('''
                        DELETE FROM Accessory_Instance_Attributes 
                        WHERE accessory_instance_id = ? AND application = ?
                    ''', (data['instance_id'], data['application']))
                else:
                    # If application is empty, delete attributes with NULL or empty application
                    db.execute('''
                        DELETE FROM Accessory_Instance_Attributes 
                        WHERE accessory_instance_id = ? AND (application IS NULL OR application = '')
                    ''', (data['instance_id'],))
            
            db.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.rollback()
            return jsonify({'success': False, 'error': str(e)})


@instances_bp.route(
    "/<int:project_id>/check_accessory_instance/<int:accessory_id>", methods=["GET"]
)
def check_accessory_instance(project_id, accessory_id):
    """Check if an accessory instance already exists for this project and accessory"""
    db = get_db()

    instance = db.execute(
        """
            SELECT ai.accessory_instance_id, ai.name, ai.short_name, ai.description,
                   ai.short_description, ai.installation
            FROM Accessory_Instance ai
            WHERE ai.project_id = ? AND ai.accessory_id = ?
            ORDER BY ai.accessory_instance_id DESC
            LIMIT 1
        """,
        (project_id, accessory_id),
    ).fetchone()

    if instance:
        # Get existing attributes
        attributes = db.execute(
            """
                SELECT name, value, application
                FROM Accessory_Instance_Attributes
                WHERE accessory_instance_id = ?
            """,
            (instance["accessory_instance_id"],),
        ).fetchall()

        return jsonify(
            {
                "exists": True,
                "instance_id": instance["accessory_instance_id"],
                "name": instance["name"],
                "short_name": instance["short_name"],
                "description": instance["description"],
                "short_description": instance["short_description"],
                "installation": instance["installation"],
                "attributes": [dict(attr) for attr in attributes],
            }
        )
    else:
        return jsonify({"exists": False})
