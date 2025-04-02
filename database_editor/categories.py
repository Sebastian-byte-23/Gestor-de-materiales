from contextlib import contextmanager
import sqlite3
import os

def init_db():
    with get_db() as conn:
        with open(os.path.join(os.path.dirname(__file__), 'main.sql'), 'r') as f:
            conn.executescript(f.read())
        conn.commit()

@contextmanager 
def get_db():
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'main.db')
    # Create database if it doesn't exist
    if not os.path.exists(db_path):
        init_db()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()

def get_categories():
    with get_db() as conn:
        cursor = conn.cursor()
        # First get all categories
        cursor.execute("""
            SELECT c.*, p.name as parent_name 
            FROM Categories c
            LEFT JOIN Categories p ON c.parent_id = p.category_id
            ORDER BY c.display_order, c.name
        """)
        all_categories = cursor.fetchall()
        
        # Organize into hierarchy
        categories_dict = {}
        root_categories = []
        
        # First pass: create dictionary of all categories
        for category in all_categories:
            category_dict = dict(category)
            category_dict['children'] = []
            categories_dict[category['category_id']] = category_dict
        
        # Second pass: organize into tree
        for category in categories_dict.values():
            if category['parent_id'] is None:
                root_categories.append(category)
            else:
                parent = categories_dict.get(category['parent_id'])
                if parent:
                    parent['children'].append(category)
        
        return root_categories

def add_category(name, parent_id, item_type='item', display_order=0):
    parent_id = int(parent_id) if parent_id else None
    display_order = int(display_order) if display_order else 0 # Ensure display_order is an integer
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO Categories (name, parent_id, item_type, display_order) VALUES (?, ?, ?, ?)",
                (name, parent_id, item_type, display_order)
            )
            conn.commit()
            return True, None
    except sqlite3.IntegrityError:
        return False, "A category with this name already exists at this level"

def edit_category(category_id, name, parent_id, linked_categories, item_type='item', display_order=0):
    parent_id = int(parent_id) if parent_id else None
    display_order = int(display_order) if display_order else 0 # Ensure display_order is an integer
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE Categories SET name = ?, parent_id = ?, linked_categories = ?, item_type = ?, display_order = ? WHERE category_id = ?",
            (name, parent_id, linked_categories, item_type, display_order, category_id)
        )
        conn.commit()

def delete_category(category_id):
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get all child categories recursively
        def get_all_child_categories(parent_id):
            cursor.execute("SELECT category_id FROM Categories WHERE parent_id = ?", (parent_id,))
            children = cursor.fetchall()
            all_children = [child['category_id'] for child in children]
            
            for child_id in list(all_children):  # Create a copy to avoid modifying during iteration
                all_children.extend(get_all_child_categories(child_id))
                
            return all_children
        
        # Get all categories to delete (the target category and all its descendants)
        categories_to_delete = [int(category_id)] + get_all_child_categories(category_id)
        
        # Delete all items in these categories
        for cat_id in categories_to_delete:
            # Delete regular items
            cursor.execute("DELETE FROM Item_Attributes WHERE item_id IN (SELECT item_id FROM Items WHERE category_id = ?)", (cat_id,))
            cursor.execute("DELETE FROM Materials WHERE item_id IN (SELECT item_id FROM Items WHERE category_id = ?)", (cat_id,))
            cursor.execute("DELETE FROM Items WHERE category_id = ?", (cat_id,))
            
            # Delete accessories
            cursor.execute("DELETE FROM Accesory_Attributes WHERE accesory_id IN (SELECT accesory_id FROM Accesory_Item WHERE category_id = ?)", (cat_id,))
            cursor.execute("DELETE FROM Materials WHERE accesory_id IN (SELECT accesory_id FROM Accesory_Item WHERE category_id = ?)", (cat_id,))
            cursor.execute("DELETE FROM Accesory_Item WHERE category_id = ?", (cat_id,))
        
        # Delete all the categories (children first, then parent)
        for cat_id in categories_to_delete:
            cursor.execute("DELETE FROM Categories WHERE category_id = ?", (cat_id,))
            
        conn.commit()

def get_category_by_id(category_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Categories WHERE category_id = ?", (category_id,))
        category = cursor.fetchone()
        return dict(category) if category else None
