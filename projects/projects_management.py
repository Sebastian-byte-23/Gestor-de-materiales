from flask import (
    send_file,
    session,
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
)
import os
import sqlite3
import json
import pytz

import uuid  # Add missing import for uuid
from .data_retrieval import (
    get_db,
    get_instances_by_category,
    get_category_tree,
    generate_category_number,
)
from datetime import datetime

projects_bp = Blueprint(
    "projects",
    __name__,
    url_prefix="/projects",
    template_folder=".",
    static_folder="static",
)


def init_db():
    DATABASE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "projects.db")
    if not os.path.exists(DATABASE):
        db = get_db()
        sql_path = os.path.join(os.path.dirname(__file__), "projects.sql")
        with open(sql_path, "r") as f:
            db.cursor().executescript(f.read())
        db.commit()
        db.close()


@projects_bp.route("/", methods=["GET", "POST"])
def projects():
    db = get_db()
    if request.method == "POST":
        name = request.form["name"]
        if not name:
            flash("Project name is required.")
        else:
            db.execute("INSERT INTO Projects (name) VALUES (?)", (name,))
            db.commit()
            return redirect(url_for("projects.projects"))

    projects = db.execute("SELECT * FROM Projects").fetchall()
    return render_template("projects.html", projects=projects)


@projects_bp.route("/<int:project_id>/edit", methods=["GET", "POST"])
def edit_project(project_id):
    db = get_db()
    if request.method == "POST":
        name = request.form["name"]
        if not name:
            flash("Project name is required")
        else:
            db.execute(
                "UPDATE Projects SET name = ?, modified_date = CURRENT_TIMESTAMP WHERE project_id = ?",
                (name, project_id),
            )
            db.commit()
            return redirect(url_for("projects.projects"))
    project = db.execute(
        "SELECT * FROM Projects WHERE project_id = ?", (project_id,)
    ).fetchone()

    if project is None:
        return "Project not found", 404  # Or redirect to an error page

    return render_template("edit_project.html", project=project)


@projects_bp.route("/<int:project_id>/delete", methods=["POST"])
def delete_project(project_id):
    db = get_db()
    db.execute("DELETE FROM Projects WHERE project_id = ?", (project_id,))
    db.commit()
    return redirect(url_for("projects.projects"))


@projects_bp.route("/<int:project_id>/categories")
def project_categories(project_id):
    # Placeholder logic.  We'll expand this later.
    db = get_db()
    project = db.execute(
        "SELECT * FROM Projects WHERE project_id = ?", (project_id,)
    ).fetchone()

    if project is None:
        return "Project not found", 404

    categories = get_category_tree()
    return render_template("categories.html", project=project, categories=categories)


@projects_bp.route("/<int:project_id>/overview")
def project_overview(project_id):
    """Generate an overview of the project suitable for PDF export"""
    db = get_db()
    main_db = sqlite3.connect(
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "main.db")
    )
    main_db.row_factory = sqlite3.Row

    # Get project details
    project = db.execute(
        "SELECT * FROM Projects WHERE project_id = ?", (project_id,)
    ).fetchone()
    if project is None:
        return "Project not found", 404

    # Get all categories with their instances
    categories = []

    def process_category_tree(category_list, parent_path=None, parent_number=None):
        result = []
        for idx, category in enumerate(category_list):
            # Get instances for this category
            instances_data = get_instances_by_category(project_id, category["id"])

            # Combine item and accessory instances
            all_instances = []

            # Generate category number
            current_number = generate_category_number(idx, parent_number)

            # Process item instances
            for item_instance in instances_data["item_instances"]:
                # Get attributes for this instance
                attrs = db.execute(
                    """
                    SELECT name, value FROM Item_Instance_Attributes 
                    WHERE instance_id = ?
                """,
                    (item_instance["instance_id"],),
                ).fetchall()

                # Get full instance details
                instance = db.execute(
                    """
                    SELECT * FROM Item_Instances WHERE instance_id = ?
                """,
                    (item_instance["instance_id"],),
                ).fetchone()

                if instance:
                    # Get linked accessories for this item instance
                    linked_accessories = []
                    accessory_instances = db.execute(
                        """
                        SELECT DISTINCT a.accessory_instance_id, a.name, a.installation,
                               a.description, a.short_description, a.accessory_id
                        FROM Accessory_Instance a
                        JOIN Accessory_Instance_Attributes attr ON a.accessory_instance_id = attr.accessory_instance_id
                        WHERE attr.application = ?
                    """,
                        (str(instance["instance_id"]),),
                    ).fetchall()

                    for acc in accessory_instances:
                        # Get accessory attributes specific to this item instance
                        acc_attrs = db.execute(
                            """
                            SELECT name, value, group_id
                            FROM Accessory_Instance_Attributes 
                            WHERE accessory_instance_id = ? AND application = ?
                        """,
                            (
                                acc["accessory_instance_id"],
                                str(instance["instance_id"]),
                            ),
                        ).fetchall()

                        # Get category name from main database
                        category_info = main_db.execute(
                            """
                            SELECT c.name 
                            FROM Accesory_Item ai
                            JOIN Categories c ON ai.category_id = c.category_id
                            WHERE ai.accesory_id = ?
                        """,
                            (acc["accessory_id"],),
                        ).fetchone()

                        # Group attributes by group_id
                        acc_attribute_groups = {}
                        for attr in acc_attrs:
                            group_id = (
                                attr["group_id"]
                                if attr["group_id"] is not None
                                else "default"
                            )
                            if group_id not in acc_attribute_groups:
                                acc_attribute_groups[group_id] = {
                                    "group_id": group_id,
                                    "application": str(instance["instance_id"]),
                                    "application_name": instance["name"],
                                    "attributes": [],
                                }
                            acc_attribute_groups[group_id]["attributes"].append(
                                {
                                    "name": attr["name"],
                                    "value": json.loads(attr["value"])[0],
                                }
                            )

                        linked_accessories.append(
                            {
                                "name": acc["name"],
                                "category_name": (
                                    category_info["name"]
                                    if category_info
                                    else "Uncategorized"
                                ),
                                "instance_id": acc["accessory_instance_id"],
                                "attribute_groups": list(acc_attribute_groups.values()),
                            }
                        )

                    # Build a dict mapping attribute names to their value for material evaluation
                    item_attr_dict = {
                        attr["name"]: json.loads(attr["value"])[0] for attr in attrs
                    }
                    from .materials_logic import get_applicable_materials

                    material_list = get_applicable_materials(
                        "item", instance["item_id"], item_attr_dict, main_db
                    )

                    all_instances.append(
                        {
                            "name": instance["name"],
                            "short_name": instance["short_name"],
                            "description": instance["description"],
                            "short_description": instance["short_description"],
                            "installation": instance["installation"],
                            "type": "Item",
                            "attributes": [
                                {
                                    "name": attr["name"],
                                    "value": json.loads(attr["value"])[0],
                                }
                                for attr in attrs
                            ],
                            "materials": material_list,
                            "linked_accessories": linked_accessories,
                        }
                    )

            # Process accessory instances
            for acc_instance in instances_data["accessory_instances"]:
                # Get full instance details
                instance = db.execute(
                    """
                    SELECT * FROM Accessory_Instance WHERE accessory_instance_id = ?
                """,
                    (acc_instance["instance_id"],),
                ).fetchone()

                if instance:
                    # Get all attributes with group_id for this accessory
                    attrs = db.execute(
                        """
                        SELECT name, value, application, group_id
                        FROM Accessory_Instance_Attributes 
                        WHERE accessory_instance_id = ?
                        ORDER BY group_id
                    """,
                        (acc_instance["instance_id"],),
                    ).fetchall()

                    # Group attributes by group_id while maintaining order
                    attribute_groups = []
                    current_group = None
                    for attr in attrs:
                        group_id = (
                            attr["group_id"]
                            if attr["group_id"] is not None
                            else str(uuid.uuid4())
                        )
                        if group_id != current_group:
                            # Get application name for display
                            application = (
                                attr["application"]
                                if attr["application"] is not None
                                else ""
                            )
                            application_name = application

                            # If application is a numeric string (item ID), look up the item name
                            if application and application.isdigit():
                                item_instance = db.execute(
                                    """
                                    SELECT name
                                    FROM Item_Instances
                                    WHERE instance_id = ?
                                """,
                                    (application,),
                                ).fetchone()

                                if item_instance:
                                    application_name = item_instance["name"]
                            # For standalone accessory with no application, use installation
                            elif not application or application == "":
                                application_name = (
                                    instance["installation"]
                                    if instance["installation"]
                                    else "General"
                                )

                            attribute_groups.append(
                                {
                                    "group_id": group_id,
                                    "application": attr["application"],
                                    "application_name": application_name,
                                    "attributes": [],
                                }
                            )
                            current_group = group_id
                        attribute_groups[-1]["attributes"].append(
                            {
                                "name": attr["name"],
                                "value": json.loads(attr["value"])[0],
                                "application": attr["application"],
                            }
                        )

                    from .materials_logic import get_applicable_materials

                    material_dict = {}
                    for group in attribute_groups:
                        # Build a dict from this group's attributes
                        group_attrs = {
                            attr["name"]: attr["value"] for attr in group["attributes"]
                        }
                        group_materials = get_applicable_materials(
                            "accessory", instance["accessory_id"], group_attrs, main_db
                        )
                        for material in group_materials:
                            material_id = material["material_id"]
                            if material_id not in material_dict:
                                material_dict[material_id] = material
                    material_list = list(material_dict.values())

                    all_instances.append(
                        {
                            "name": instance["name"],
                            "short_name": instance["short_name"],
                            "description": instance["description"],
                            "short_description": instance["short_description"],
                            "installation": instance["installation"],
                            "type": "Accessory",
                            "attribute_groups": attribute_groups,
                            "materials": material_list,
                        }
                    )

            # Sort instances by name
            all_instances.sort(key=lambda x: x["name"])

            # Process subcategories recursively
            subcategories = []
            if "children" in category:
                subcategories = process_category_tree(
                    category["children"],
                    parent_path=(
                        parent_path + [category["name"]]
                        if parent_path
                        else [category["name"]]
                    ),
                    parent_number=current_number,
                )

            # Create category object with instances and subcategories
            cat_obj = {
                "id": category["id"],
                "name": category["name"],
                "instances": all_instances,
                "subcategories": subcategories,
                "number": current_number,
                "path": (
                    parent_path + [category["name"]]
                    if parent_path
                    else [category["name"]]
                ),
            }

            # Only add categories that have instances or subcategories with instances
            has_instances = bool(all_instances)
            # Check if any subcategories have instances (recursively)
            has_subcategories_with_instances = len(subcategories) > 0

            if has_instances or has_subcategories_with_instances:
                result.append(cat_obj)

        return result

    # Get the category tree and process it
    category_tree = get_category_tree()
    categories = process_category_tree(category_tree)

    # No need to filter categories as we're already only including those with instances or subcategories

    # Close the main database connection
    main_db.close()

    return render_template("overall_view.html", project=project, categories=categories)


# Import and register routes from other modules
from .data_retrieval import register_routes as register_data_routes
from .instances_management import register_routes as register_instances_routes

# Register all routes
register_data_routes(projects_bp)
register_instances_routes(projects_bp)

from .generate_project_pdf import generate_project_pdf


@projects_bp.route("/<int:project_id>/generate_pdf/<report_type>")
def generate_project_pdf_route(project_id, report_type):
    """Generate a PDF for the project and send it as a download"""

    # Validate report type
    if report_type not in ["commercial", "full"]:
        report_type = "full"  # Default to full report

    # Get project name for the filename
    db = get_db()
    project = db.execute(
        "SELECT name FROM Projects WHERE project_id = ?", (project_id,)
    ).fetchone()
    if not project:
        return "Project not found", 404

    # Format the date
    from datetime import datetime

    current_date = datetime.now().strftime("%Y.%m.%d")

    # Generate a filename based on the project name and report type
    if report_type == "commercial":
        output_filename = f"[{current_date}] EETT {project['name']}.pdf"
    else:  # full report
        output_filename = f"[{current_date}] EETT Full {project['name']}.pdf"
    output_dir = os.path.join(os.path.dirname(__file__), "pdf_output")

    # Create the output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    output_path = os.path.join(output_dir, output_filename)

    # Print database paths for debugging
    # import os # Removed redundant import

    projects_db_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "projects.db"
    )
    main_db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "main.db")

    print(
        f"Projects DB path: {projects_db_path} (exists: {os.path.exists(projects_db_path)})"
    )
    print(f"Main DB path: {main_db_path} (exists: {os.path.exists(main_db_path)})")

    # Generate the PDF with specified report type
    generate_project_pdf(project_id, output_path, report_type)

    # Send the file as a download
    return send_file(
        output_path,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=output_filename,
    )


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
    timestamp = datetime.utcnow().isoformat()
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


@projects_bp.route("/<int:project_id>/history")
def project_history(project_id):
    db = get_db()
    logs = db.execute(
        """
        SELECT l.*, u.username
        FROM project_operations_log l
        JOIN users u ON u.id = l.user_id
        WHERE l.project_id = ?
        ORDER BY l.timestamp DESC
    """,
        (project_id,),
    ).fetchall()

    project = db.execute(
        "SELECT name FROM Projects WHERE project_id = ?", (project_id,)
    ).fetchone()
    project_name = project["name"] if project else f"Proyecto {project_id}"

    return render_template(
        "project_history.html",
        logs=logs,
        project_id=project_id,
        project_name=project_name,
    )


def log_operation(db, project_id, user_id, action_type, instance_type, instance_id, instance_name, changes):
    chile_tz = pytz.timezone("America/Santiago")
    timestamp = datetime.now(chile_tz).strftime("%Y-%m-%d %H:%M:%S")

    for field, (old, new) in changes.items():
        db.execute("""
            INSERT INTO project_operations_log (
                project_id, user_id, timestamp, action_type,
                instance_type, instance_id, instance_name,
                field_changed, old_value, new_value
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            project_id, user_id, timestamp, action_type,
            instance_type, instance_id, instance_name,
            field, old, new
        ))
    db.commit()


def detectar_cambios(actual, nuevo_dict, campos):
    cambios = {}
    for campo in campos:
        viejo = actual[campo]
        nuevo = nuevo_dict.get(campo)
        if viejo != nuevo:
            cambios[campo] = (viejo, nuevo)
    return cambios

    # -------------------------------
    # RUTA PARA ACTUALIZAR INSTANCIA
    # -------------------------------


@projects_bp.route("/update_instance", methods=["POST"])
def update_instance():
    data = request.json
    db = get_db()

    try:
        instance_id = data["instance_id"]

        if "instance_type" in data:
            instance_type = data["instance_type"]
        else:
            item_instance = db.execute(
                "SELECT instance_id FROM Item_Instances WHERE instance_id = ?",
                (instance_id,),
            ).fetchone()
            instance_type = "item" if item_instance else "accessory"

        if instance_type == "item":
            original = db.execute(
                "SELECT * FROM Item_Instances WHERE instance_id = ?", (instance_id,)
            ).fetchone()
        else:
            original = db.execute(
                "SELECT * FROM Accessory_Instance WHERE accessory_instance_id = ?",
                (instance_id,),
            ).fetchone()

        campos_a_comparar = [
            "name",
            "short_name",
            "description",
            "short_description",
            "installation",
        ]
        changes = detectar_cambios(original, data, campos_a_comparar)

        # -----------------------
        # ITEM INSTANCE
        # -----------------------
        if instance_type == "item":
            db.execute(
                """
                UPDATE Item_Instances
                SET name = ?, short_name = ?, description = ?, short_description = ?, installation = ?
                WHERE instance_id = ?
            """,
                (
                    data["name"],
                    data["short_name"],
                    data["description"],
                    data["short_description"],
                    data["installation"],
                    instance_id,
                ),
            )

            form_attr_names = set(data["attributes"].keys())

            existing_attrs = db.execute(
                """
                SELECT name, value FROM Item_Instance_Attributes WHERE instance_id = ?
            """,
                (instance_id,),
            ).fetchall()

            existing_attr_values = {
                attr["name"]: attr["value"] for attr in existing_attrs
            }
            existing_attr_names = set(existing_attr_values.keys())

            # Eliminar atributos eliminados
            attrs_to_delete = existing_attr_names - form_attr_names
            for name in attrs_to_delete:
                db.execute(
                    """
                    DELETE FROM Item_Instance_Attributes
                    WHERE instance_id = ? AND name = ?
                """,
                    (instance_id, name),
                )

            # Insertar o actualizar atributos
            for name, value in data["attributes"].items():
                value_json = json.dumps([value])
                old_json = existing_attr_values.get(name)

                if name in existing_attr_names:
                    db.execute(
                        """
                        UPDATE Item_Instance_Attributes
                        SET value = ?
                        WHERE instance_id = ? AND name = ?
                    """,
                        (value_json, instance_id, name),
                    )
                else:
                    db.execute(
                        """
                        INSERT INTO Item_Instance_Attributes (instance_id, name, value)
                        VALUES (?, ?, ?)
                    """,
                        (instance_id, name, value_json),
                    )

                if old_json != value_json:
                    changes[f"attr:{name}"] = (old_json, value_json)

        # -----------------------
        # ACCESSORY INSTANCE
        # -----------------------
        else:
            db.execute(
                """
                UPDATE Accessory_Instance
                SET name = ?, short_name = ?, description = ?, short_description = ?, installation = ?
                WHERE accessory_instance_id = ?
            """,
                (
                    data["name"],
                    data["short_name"],
                    data["description"],
                    data["short_description"],
                    data["installation"],
                    instance_id,
                ),
            )

            existing_attrs = db.execute(
                """
                SELECT name, value, application, group_id FROM Accessory_Instance_Attributes
                WHERE accessory_instance_id = ?
            """,
                (instance_id,),
            ).fetchall()

            existing_attr_lookup = {
                f"{attr['name']}_{attr['application'] or 'General'}": attr
                for attr in existing_attrs
            }

            application = data.get("application", "")
            group_id = data.get("group_id")
            if not group_id and existing_attrs and existing_attrs[0]["group_id"]:
                group_id = existing_attrs[0]["group_id"]
            if not group_id:
                group_id = str(uuid.uuid4())

            for name, value in data["attributes"].items():
                key = f"{name}_{application or 'General'}"
                value_json = json.dumps([value])
                old_attr = existing_attr_lookup.get(key)

                if old_attr:
                    db.execute(
                        """
                        UPDATE Accessory_Instance_Attributes
                        SET value = ?, group_id = ?
                        WHERE accessory_instance_id = ? AND name = ? AND
                              (application = ? OR (application IS NULL AND ? = 'General'))
                    """,
                        (
                            value_json,
                            group_id,
                            instance_id,
                            name,
                            application,
                            "General",
                        ),
                    )
                    if old_attr["value"] != value_json:
                        changes[f"attr:{name}"] = (old_attr["value"], value_json)
                else:
                    db.execute(
                        """
                        INSERT INTO Accessory_Instance_Attributes (accessory_instance_id, name, value, application, group_id)
                        VALUES (?, ?, ?, ?, ?)
                    """,
                        (instance_id, name, value_json, application, group_id),
                    )
                    changes[f"attr:{name}"] = (None, value_json)

        # -----------------------
        # REGISTRAR CAMBIOS
        # -----------------------
        db.commit()

        if changes:
            log_operation(
                db=db,
                project_id=data["project_id"],
                user_id=session.get("user_id"),
                action_type="update",
                instance_type=instance_type,
                instance_id=instance_id,
                instance_name=data["name"],
                changes=changes,
            )

        return jsonify({"success": True})

    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)})


