"""RackForgePrime — cœur Python.

Package pur (aucune dépendance au serveur web) : modèle de données,
moteur de placement U, catalogue, exports SVG/PDF, stockage local.
"""

from .models import (  # noqa: F401
    SCHEMA_VERSION,
    U_MM,
    EquipmentType,
    Project,
    Rack,
    RackItem,
    free_positions,
    patch_table,
    rack_stats,
    type_index,
    validate_placement,
)

__version__ = "0.1.0"
