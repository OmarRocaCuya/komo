"""Komo: motor de sustitución nutricional (prototipo para el CUMIS Churubamba 2026)."""

from .motor import recomendar
from .requerimientos import Persona, calcular

__all__ = ["recomendar", "Persona", "calcular"]
