import json

def condition_matches(instance_value, operator, condition_value):
    if operator == '=':
        return instance_value == condition_value
    elif operator == '>':
        try:
            return float(instance_value) > float(condition_value)
        except ValueError:
            return instance_value > condition_value
    elif operator == '<':
        try:
            return float(instance_value) < float(condition_value)
        except ValueError:
            return instance_value < condition_value
    elif operator.upper() == 'IN':
        try:
            values = json.loads(condition_value)
            if not isinstance(values, list):
                values = [values]
        except Exception:
            values = [x.strip() for x in condition_value.split(',')]
        return instance_value in values
    elif operator.upper() == 'BETWEEN':
        parts = [x.strip() for x in condition_value.split(',')]
        if len(parts) != 2:
            return False
        try:
            lower, upper = float(parts[0]), float(parts[1])
            return lower <= float(instance_value) <= upper
        except ValueError:
            return False
    elif operator.upper() == 'IS NOT NULL':
        return instance_value is not None and instance_value != ''
    else:
        return False

def evaluate_material_conditions(conditions, instance_attributes):
    # conditions is a list of rows (as dicts) for this group.
    for cond in conditions:
        attr_name = cond['attribute_name']
        operator = cond['operator']
        cond_value = cond['value']
        inst_value = instance_attributes.get(attr_name)
        if inst_value is None or not condition_matches(str(inst_value), operator, str(cond_value)):
            return False
    return True

def get_applicable_materials(instance_type, ref_id, instance_attributes, main_db):
    """
    instance_type: 'item' or 'accessory'
    ref_id: For items, pass the item_id; for accessories, pass the accesory_id.
    instance_attributes: dict mapping attribute names to their values.
    main_db: sqlite3 connection to main.db.
    Returns: a list of material dicts (e.g. containing material_name and SKU).
    """
    cursor = main_db.cursor()
    if instance_type == 'item':
        cursor.execute("SELECT * FROM Materials WHERE item_id = ?", (ref_id,))
    else:
        cursor.execute("SELECT * FROM Materials WHERE accesory_id = ?", (ref_id,))
    materials = cursor.fetchall()
    applicable = []
    for material in materials:
        material_dict = dict(material)
        cursor.execute("SELECT * FROM Material_Conditions WHERE material_id = ?", (material_dict['material_id'],))
        conditions = cursor.fetchall()
        if not conditions:
            # No conditions means the material applies automatically.
            applicable.append(material_dict)
            continue

        # Group conditions by group_id
        groups = {}
        for cond in conditions:
            cond_dict = dict(cond)
            groups.setdefault(cond_dict['group_id'], []).append(cond_dict)
        
        for group in groups.values():
            if evaluate_material_conditions(group, instance_attributes):
                applicable.append(material_dict)
                break
    return applicable
