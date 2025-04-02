import os
import sys
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from flask import (
    Blueprint,
    session,
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    jsonify,
    flash,
    g,
)
from jinja2 import ChoiceLoader, FileSystemLoader
from functools import partial
from database_editor.items import get_items_by_category, edit_item, edit_item_attribute
from accessories import (
    get_accessories_by_category,
    edit_accessory,
    edit_accessory_attribute,
)
from categories import (
    get_categories,
    add_category,
    edit_category,
    delete_category,
    get_db,
    get_category_by_id,
)
from items import add_item, add_item_attribute, get_items_by_category
from accessories import (
    add_accessory,
    add_accessory_attribute,
    get_accessories_by_category,
)
import sqlite3
import json
from datetime import datetime
from materials import (
    get_materials_for_item,
    add_material,
    edit_material,
    delete_material,
    add_material_condition,
    edit_material_condition,
    delete_material_condition,
    edit_material_units,
)
from windows import (
    get_windows_by_category,
    get_window_by_id,
    save_window,
    delete_window,
    get_window_groups,
)

# Import the blueprints from the projects package
from projects import projects_bp, instances_bp, data_retrieval_bp

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev"

DATABASE = "../projects.db"  # Change this to a random secret key in production
app.jinja_loader = ChoiceLoader(
    [
        FileSystemLoader(os.path.join(app.root_path, "database_editor_templates")),
        FileSystemLoader(
            os.path.join(app.root_path, "..", "projects")
        ),  # Keep this for direct access
        FileSystemLoader(
            os.path.join(app.root_path, "..", "projects", "templates")
        ),  # Add templates directory
        FileSystemLoader(
            os.path.join(app.root_path, "..")
        ),  # Add this to access blueprint templates
    ]
)

# Register all blueprints from the split project structure
app.register_blueprint(projects_bp)
app.register_blueprint(instances_bp)
app.register_blueprint(data_retrieval_bp)

# Configure template loaders to find templates from all modules
app.jinja_loader = ChoiceLoader(
    [
        FileSystemLoader(os.path.join(app.root_path, "database_editor_templates")),
        FileSystemLoader(os.path.join(app.root_path, "..", "projects")),
        FileSystemLoader(os.path.join(app.root_path, "..", "projects", "templates")),
        FileSystemLoader(os.path.join(app.root_path, "..")),
    ]
)


@app.route("/")
def landing():
    if g.user is None:
        return redirect(url_for("login"))

    return render_template("landing.html", user=g.user)


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


@app.before_request
def load_logged_in_user():
    user_id = session.get("user_id")

    if user_id is None:
        g.user = None
    else:
        g.user = (
            get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        )


# Ruta login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = (
            get_db()
            .execute("SELECT * FROM users WHERE username = ?", (username,))
            .fetchone()
        )

        error = None
        if user is None:
            error = "Usuario incorrecto."
        elif not check_password_hash(user["password_hash"], password):
            error = "Contraseña incorrecta."

        if error is None:
            session.clear()
            session["user_id"] = user["id"]
            # Redirige aquí a la landing para escoger editor después del login
            return redirect(url_for("landing"))

        return render_template("login.html", error=error)

    return render_template("login.html")


# Ruta del editor de proyectos protegida con login
@app.route("/editor")
def project_editor():
    if g.user is None:
        return redirect(url_for("login"))

    return render_template("project_editor.html", user=g.user)


# Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/database_editor")
def database_editor():
    categories = get_categories()
    return render_template(
        "index.html",
        categories=categories,
        get_items_by_category=get_items_by_category,
        get_accessories_by_category=get_accessories_by_category,
    )


@app.route("/get_categories")
def get_categories_json():
    categories = get_categories()
    # Ensure each category has an item_type field
    for category in categories:
        if "item_type" not in category:
            category["item_type"] = category.get("item_type", "item")
    return jsonify(categories)


@app.route("/category/<int:category_id>/item_type")
def get_category_item_type(category_id):
    """Get the item_type of a category."""
    category = get_category_by_id(category_id)
    if category:
        return jsonify({"item_type": category["item_type"]})
    return jsonify({"error": "Category not found"}), 404


@app.route("/edit_category/<int:category_id>", methods=["POST"])
def edit_category_route(category_id):
    name = request.form["name"]
    parent_id = request.form["parent_id"]
    linked_categories = request.form["linked_categories"]
    item_type = request.form.get("item_type", "item")
    display_order = request.form.get("display_order", 0) # Get display_order from form
    edit_category(category_id, name, parent_id, linked_categories, item_type, display_order)
    return redirect(url_for("database_editor"))


@app.route("/update_category_order", methods=["POST"])
def update_category_order_route():
    data = request.json
    category_id = data.get("category_id")
    new_parent_id = data.get("new_parent_id")
    sibling_ids = data.get("sibling_ids") # List of category IDs in the new order

    if not category_id or sibling_ids is None:
        return jsonify({"success": False, "message": "Missing data"}), 400

    try:
        # Import the function to update order
        from database_editor.categories import update_category_order
        success, message = update_category_order(category_id, new_parent_id, sibling_ids)
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "message": message}), 500
    except Exception as e:
        # Log the exception e
        print(f"Error updating category order: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/delete_category/<int:category_id>", methods=["POST"])
def delete_category_route(category_id):
    delete_category(category_id)
    return redirect(url_for("database_editor"))


@app.route("/add_category", methods=["POST"])
def add_category_route():
    name = request.form["name"]
    parent_id = request.form["parent_id"]
    item_type = request.form.get("item_type", "item")
    display_order = request.form.get("display_order", 0) # Get display_order from form
    success, error = add_category(name, parent_id, item_type, display_order)

    if not success:
        return error, 400

    return redirect(url_for("database_editor"))


@app.route("/edit_item", methods=["POST", "DELETE"])
def edit_item_route():
    data = request.json
    if data["type"] == "item":
        edit_item(
            data["id"],
            data["name"],
            data["short_name"],
            data["description"],
            data["short_description"],
            data["installation"],
            data["category_id"],
        )
        # Update attributes
        edit_item_attribute(data["id"], data["attributes"])
    else:
        edit_accessory(
            data["id"],
            data["name"],
            data["short_name"],
            data["description"],
            data["short_description"],
            data["installation"],
            data["category_id"],
        )
        # Update attributes
        edit_accessory_attribute(data["id"], data["attributes"])

    return jsonify({"success": True})


@app.route("/delete_item/<int:item_id>/<string:item_type>", methods=["POST"])
def delete_item_route(item_id, item_type):
    if item_type == "item":
        from database_editor.items import delete_item

        delete_item(item_id)
    else:
        from database_editor.accessories import delete_accessory

        delete_accessory(item_id)
    return jsonify({"success": True})


@app.route("/add_item", methods=["POST"])
def add_item_route():
    data = request.json
    if data["type"] == "item":
        item_id = add_item(
            data["name"],
            data["short_name"],
            data["description"],
            data["short_description"],
            data["installation"],
            data["category_id"],
        )

        # Add attributes
        for attr in data.get("attributes", []):
            add_item_attribute(item_id, attr["name"], attr["value"])

        return jsonify({"success": True, "item_id": item_id})

    elif data["type"] == "accessory":
        accessory_id = add_accessory(
            data["name"],
            data["short_name"],
            data["description"],
            data["short_description"],
            data["installation"],
            data["category_id"],
        )

        # Add attributes
        for attr in data.get("attributes", []):
            add_accessory_attribute(accessory_id, attr["name"], attr["value"])

        return jsonify({"success": True, "accessory_id": accessory_id})


@app.route("/materials_edit/<int:item_id>/<string:item_type>", methods=["GET"])
def materials_edit(item_id, item_type):
    materials = get_materials_for_item(item_id, item_type)

    item_attributes = {}
    with get_db() as conn:
        cursor = conn.cursor()
        # Retrieve the item's name based on its type
        if item_type == "item":
            cursor.execute("SELECT name FROM Items WHERE item_id = ?", (item_id,))
        else:
            cursor.execute(
                "SELECT name FROM Accesory_Item WHERE accesory_id = ?", (item_id,)
            )
        row = cursor.fetchone()
        item_name = row["name"] if row else "Unknown"
        if item_type == "item":
            cursor.execute(
                "SELECT name, value FROM Item_Attributes WHERE item_id = ?", (item_id,)
            )
        else:
            cursor.execute(
                "SELECT name, value FROM Accesory_Attributes WHERE accesory_id = ?",
                (item_id,),
            )
        for row in cursor.fetchall():
            row = dict(row)
            item_attributes[row["name"]] = json.loads(row["value"])

    return render_template(
        "materials_edit.html",
        item_id=item_id,
        item_type=item_type,
        item_name=item_name,
        materials=materials,
        item_attributes=item_attributes,
    )


@app.route("/materials/add", methods=["POST"])
def add_material_route():
    data = request.json
    material_id = add_material(
        data["item_id"], data["item_type"], data["material_name"], data["SKU"]
    )
    return jsonify({"success": True, "material_id": material_id})


@app.route("/materials/edit", methods=["POST"])
def edit_material_route():
    data = request.json
    edit_material(data["material_id"], data["material_name"], data["SKU"])
    return jsonify({"success": True})


@app.route("/materials/delete", methods=["POST"])
def delete_material_route():
    data = request.json
    delete_material(data["material_id"])
    return jsonify({"success": True})


@app.route("/materials/condition/add", methods=["POST"])
def add_material_condition_route():
    data = request.json
    condition_id = add_material_condition(
        data["material_id"],
        data["group_id"],
        data["attribute_name"],
        data["operator"],
        data["value"],
    )
    return jsonify({"success": True, "condition_id": condition_id})


@app.route("/materials/condition/edit", methods=["POST"])
def edit_material_condition_route():
    data = request.json
    edit_material_condition(
        data["condition_id"],
        data["group_id"],
        data["attribute_name"],
        data["operator"],
        data["value"],
    )
    return jsonify({"success": True})


@app.route("/materials/condition/delete", methods=["POST"])
def delete_material_condition_route():
    data = request.json
    delete_material_condition(data["condition_id"])
    return jsonify({"success": True})


@app.route("/materials/units/edit", methods=["POST"])
def edit_material_units_route():
    data = request.json
    material_id = data["material_id"]
    units = data["units"]
    if units not in ["UN", "ML", "KG"]:
        return jsonify({"success": False, "message": "Invalid units value"}), 400
    edit_material_units(material_id, units)
    return jsonify({"success": True})


# Window routes
@app.route("/window_designer/<int:category_id>", defaults={"window_id": None})
@app.route("/window_designer/<int:category_id>/<int:window_id>")
def window_designer(category_id, window_id):
    # Get category info to verify it's a window category
    category = get_category_by_id(category_id)
    if not category or category["item_type"] != "window":
        # For now, we'll allow any category to create windows
        pass

    # Get window data if editing
    window = None
    if window_id:
        window = get_window_by_id(window_id)
        if not window:
            return redirect("/")

    # Get all window groups for the dropdown
    window_groups = get_window_groups()

    return render_template(
        "windows.html",
        category_id=category_id,
        window_id=window_id,
        window=window,
        window_groups=window_groups,
    )


@app.route("/window/<int:window_id>")
def get_window_json(window_id):
    """Get window data as JSON for AJAX requests"""
    window = get_window_by_id(window_id)
    if window:
        return jsonify(window)
    return jsonify({"error": "Window not found"}), 404


@app.route("/window_list/<int:category_id>")
def window_list(category_id):
    # Get category info from main.db
    category = get_category_by_id(category_id)

    # Get all windows for this category from main.db
    windows = get_windows_by_category(category_id)

    # Get finish and profile options from Window_Specs table
    from database_editor.windows import get_window_specs

    finish_options = get_window_specs("finish")
    profile_options = get_window_specs("profile")

    # Ensure we have at least one default option for each
    if not finish_options:
        finish_options = ["white", "black", "brown"]
    if not profile_options:
        profile_options = ["C60", "C70", "C80"]

    return render_template(
        "window_list.html",
        category_id=category_id,
        category=category,
        windows=windows,
        finish_options=finish_options,
        profile_options=profile_options,
    )


@app.route("/save_window", methods=["POST"])
def save_window_route():
    # Ensure we're saving to main.db
    data = request.json

    # Log the data being received
    print(f"Saving window data: {data}")

    success, window_id, error = save_window(data)

    if success:
        print(f"Window saved successfully with ID: {window_id}")
        return jsonify({"success": True, "window_id": window_id})
    else:
        print(f"Error saving window: {error}")
        return jsonify({"success": False, "message": error})


@app.route("/delete_window/<int:window_id>", methods=["POST"])
def delete_window_route(window_id):
    success, category_id, error = delete_window(window_id)

    if success:
        return jsonify({"success": True, "category_id": category_id})
    else:
        return jsonify({"success": False, "message": error})


@app.route("/save_window_spec", methods=["POST"])
def save_window_spec_route():
    """Save a new window spec option to the database"""
    from database_editor.windows import save_window_spec, get_window_specs

    data = request.json
    spec_name = data.get("spec_name")
    new_value = data.get("value")

    if not spec_name or not new_value:
        return jsonify({"success": False, "message": "Missing spec_name or value"}), 400

    # Get current values
    current_values = get_window_specs(spec_name)

    # Add new value if it doesn't already exist
    if new_value not in current_values:
        current_values.append(new_value)

        # Save updated values
        success, error = save_window_spec(spec_name, current_values)

        if success:
            return jsonify({"success": True, "values": current_values})
        else:
            return jsonify({"success": False, "message": error}), 500

    return jsonify({"success": True, "values": current_values})


@app.route("/delete_window_spec", methods=["POST"])
def delete_window_spec_route():
    """Delete a window spec option from the database"""
    from database_editor.windows import save_window_spec, get_window_specs

    data = request.json
    spec_name = data.get("spec_name")
    value_to_delete = data.get("value")

    if not spec_name or not value_to_delete:
        return jsonify({"success": False, "message": "Missing spec_name or value"}), 400

    # Get current values
    current_values = get_window_specs(spec_name)

    # Remove value if it exists
    if value_to_delete in current_values:
        current_values.remove(value_to_delete)

        # Save updated values
        success, error = save_window_spec(spec_name, current_values)

        if success:
            return jsonify({"success": True, "values": current_values})
        else:
            return jsonify({"success": False, "message": error}), 500

    return jsonify({"success": True, "values": current_values})


@app.route("/duplicate_window/<int:window_id>", methods=["POST"])
def duplicate_window_route(window_id):
    from database_editor.windows import get_window_by_id
    import sqlite3
    import json
    import os

    # Get the window from main.db
    window = get_window_by_id(window_id)
    if not window:
        return jsonify({"success": False, "message": "Window not found"}), 404

    # Get project_id from request, default to 1 if not provided
    project_id = request.args.get("project_id", 1, type=int)

    # Get finish and profile from request parameters
    finish = request.args.get("finish", "white")
    profile = request.args.get("profile", "C60")

    try:
        # Connect to the projects database
        projects_db_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "projects.db"
        )
        conn = sqlite3.connect(projects_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Prepare pane_states as JSON
        pane_states_json = json.dumps(window.get("pane_states", {}))

        # Insert the window into the projects database
        cursor.execute(
            """
            INSERT INTO Windows 
            (project_id, name, total_height, total_width, bottom_height, left_width, 
             window_type, category_id, pane_states, finish, profile)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                project_id,
                window["name"],
                window["total_height"],
                window["total_width"],
                window.get("bottom_height", 400),
                window.get("left_width", 500),
                window["window_type"],
                window["category_id"],
                pane_states_json,
                finish,
                profile,
            ),
        )

        new_window_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return jsonify({"success": True, "window_id": new_window_id})
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({"success": False, "message": str(e)})


@app.route("/generate_window_svg", methods=["POST"])
def generate_window_svg():
    """Generate SVG for a window based on parameters"""
    from database_editor.window_drawing import generate_svg

    params = request.json
    svg_data = generate_svg(params)
    return jsonify({"svg": svg_data})


if __name__ == "__main__":
    app.run(debug=True)
from database_editor.window_drawing import generate_svg


@app.route("/projects/windows/<int:project_id>")
def get_project_windows_json(project_id):
    """Get all windows for a project as JSON"""
    from projects.data_retrieval import get_project_windows

    windows = get_project_windows(project_id)
    return jsonify({"windows": windows})


def add_svg_to_windows(windows):
    for window in windows:
        params = {
            "window_type": window["window_type"],
            "total_height": window["total_height"],
            "total_width": window["total_width"],
            "bottom_height": window.get("bottom_height", 400),
            "left_width": window.get("left_width", 500),
            "pane_states": window.get(
                "pane_states", {}
            ),  # ensure this is a dict with keys like 'pane_single', etc.
        }
        window["svg"] = generate_svg(params)


