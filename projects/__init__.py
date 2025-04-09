from .data_retrieval import data_retrieval_bp
from .instances_management import instances_bp
from .projects_management import projects_bp
from .bom_routes import bom_bp, register_bom_routes

# Register BOM routes with the projects blueprint
register_bom_routes(projects_bp)

__all__ = ['projects_bp', 'instances_bp', 'data_retrieval_bp', 'bom_bp']
