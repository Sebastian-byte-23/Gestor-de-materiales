-- this is the database that we use to store project specific information, going from the projects themselves down to their details such as which instances they have
CREATE TABLE Projects (
    project_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    modified_date DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TRIGGER update_projects_modified_date
AFTER UPDATE ON Projects
FOR EACH ROW
BEGIN
    UPDATE Projects SET modified_date = CURRENT_TIMESTAMP WHERE project_id = OLD.project_id;
END;

CREATE TABLE Item_Instances (
    instance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,  -- References main.db Items.item_id
    name VARCHAR(50) NOT NULL,
    short_name VARCHAR(50),
    description TEXT,
    short_description TEXT,
    installation TEXT,
    hidden TEXT DEFAULT '[]',
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    modified_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES Projects(project_id) ON DELETE CASCADE
);

CREATE TRIGGER update_item_instances_modified_date
AFTER UPDATE ON Item_Instances
FOR EACH ROW
BEGIN
    UPDATE Item_Instances SET modified_date = CURRENT_TIMESTAMP WHERE instance_id = OLD.instance_id;
END;

-- Item Instance Attributes Table (snapshot of original item attributes)
CREATE TABLE Item_Instance_Attributes (
    attribute_id INTEGER PRIMARY KEY AUTOINCREMENT,
    instance_id INTEGER NOT NULL,
    name VARCHAR(50) NOT NULL,
    value TEXT DEFAULT '[]',
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    modified_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (instance_id) REFERENCES Item_Instances(instance_id) ON DELETE CASCADE
);

CREATE TRIGGER update_item_instance_attributes_modified_date
AFTER UPDATE ON Item_Instance_Attributes
FOR EACH ROW
BEGIN
    UPDATE Item_Instance_Attributes SET modified_date = CURRENT_TIMESTAMP WHERE attribute_id = OLD.attribute_id;
END;

-- Accessory Instance Table
CREATE TABLE Accessory_Instance (
    accessory_instance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    accessory_id INTEGER NOT NULL,  -- References main.db Accessory_Item.accessory_id
    name VARCHAR(50) NOT NULL,
    short_name VARCHAR(50),
    description TEXT,
    short_description TEXT,
    installation TEXT,
    hidden TEXT DEFAULT '[]',
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    modified_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES Projects(project_id) ON DELETE CASCADE
);

CREATE TRIGGER update_accessory_instance_modified_date
AFTER UPDATE ON Accessory_Instance
FOR EACH ROW
BEGIN
    UPDATE Accessory_Instance SET modified_date = CURRENT_TIMESTAMP WHERE accessory_instance_id = OLD.accessory_instance_id;
END;

-- Accessory Instance Attributes Table
CREATE TABLE Accessory_Instance_Attributes (
    attribute_id INTEGER PRIMARY KEY AUTOINCREMENT,
    accessory_instance_id INTEGER NOT NULL,
    application TEXT,
    name VARCHAR(50) NOT NULL,
    value TEXT DEFAULT '[]',
    group_id TEXT
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    modified_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (accessory_instance_id) REFERENCES Accessory_Instance(accessory_instance_id) ON DELETE CASCADE
);

-- Windows Instance Table
CREATE TABLE Windows (
    window_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    total_height INTEGER NOT NULL,
    total_width INTEGER NOT NULL,
    bottom_height INTEGER,
    left_width INTEGER,
    window_type VARCHAR(20) NOT NULL, -- 'single-pane', 'two-pane', 'two-pane-vertical', 'three-pane'
    category_id INTEGER NOT NULL,
    pane_states TEXT,
	finish TEXT,
	profile TEXT
);

CREATE TABLE project_operations_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    timestamp TEXT NOT NULL,
    action_type TEXT NOT NULL,
    instance_type TEXT NOT NULL,
    instance_id INTEGER NOT NULL,
    instance_name TEXT NOT NULL,
    field_changed TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(project_id) REFERENCES projects(project_id)
);


 CREATE TABLE Bill_Of_Materials (
     bom_id INTEGER PRIMARY KEY AUTOINCREMENT,
     project_id INTEGER NOT NULL,
     material_id INTEGER NOT NULL,  -- References main.db Materials.material_id
     quantity REAL NOT NULL,
     unit VARCHAR(50),
     FOREIGN KEY (project_id) REFERENCES Projects(project_id) ON DELETE CASCADE
     -- No Foreign Key constraint to main.db to avoid cross-database constraints
 );

 CREATE INDEX idx_bom_project_id ON Bill_Of_Materials(project_id);
 CREATE INDEX idx_bom_material_id ON Bill_Of_Materials(material_id);

CREATE TRIGGER update_accessory_instance_attributes_modified_date
AFTER UPDATE ON Accessory_Instance_Attributes
FOR EACH ROW
BEGIN
    UPDATE Accessory_Instance_Attributes SET modified_date = CURRENT_TIMESTAMP WHERE attribute_id = OLD.attribute_id;
END;

CREATE INDEX idx_item_instances ON Item_Instances(project_id);
CREATE INDEX idx_accessory_instances ON Accessory_Instance(project_id);
CREATE INDEX idx_item_instance_attrs ON Item_Instance_Attributes(instance_id);
CREATE INDEX idx_accessory_instance_attrs ON Accessory_Instance_Attributes(accessory_instance_id);
CREATE INDEX idx_accessory_group_id ON Accessory_Instance_Attributes(group_id);
