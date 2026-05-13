from abc import ABC, abstractmethod
from datetime import datetime
import json
import os
import re
from typing import Any, Dict, Optional

LOG_PATH = os.path.join(os.path.dirname(__file__), "logs", "application.log")


class EventLogger:
    """Registro de eventos y errores en archivo."""

    @staticmethod
    def _ensure_log_directory() -> None:
        log_dir = os.path.dirname(LOG_PATH)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

    @staticmethod
    def log_event(message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        EventLogger._ensure_log_directory()
        payload = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "type": "EVENT",
            "message": message,
            "details": extra or {},
        }
        with open(LOG_PATH, "a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(payload, ensure_ascii=False) + "\n")

    @staticmethod
    def log_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        EventLogger._ensure_log_directory()
        payload = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "type": "ERROR",
            "error_type": type(error).__name__,
            "message": str(error),
            "context": context or {},
        }
        with open(LOG_PATH, "a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(payload, ensure_ascii=False) + "\n")


class SoftwareFJError(Exception):
    """Base para excepciones personalizadas de Software FJ."""


class ValidationError(SoftwareFJError):
    """Datos inválidos o parámetros faltantes."""


class ClientRegistrationError(SoftwareFJError):
    """Error en el registro o modificación de un cliente."""


class ServiceUnavailableError(SoftwareFJError):
    """Servicio no disponible o parámetros incorrectos."""


class ReservationError(SoftwareFJError):
    """Errores relacionados con la gestión de reservas."""


class CostCalculationError(SoftwareFJError):
    """Errores en cálculo de costos o descuentos."""


class Entity(ABC):
    """Clase abstracta para entidades generales del sistema."""

    def __init__(self, identifier: str) -> None:
        self.identifier = identifier
        self.validate_identifier(identifier)

    @staticmethod
    def validate_identifier(identifier: str) -> None:
        if not identifier or not isinstance(identifier, str):
            raise ValidationError("Identificador inválido o ausente.")

    @abstractmethod
    def describe(self) -> str:
        pass


class Client(Entity):
    """Representa un cliente con información privada y validaciones."""

    def __init__(self, identifier: str, name: str, email: str, phone: str, document: str) -> None:
        super().__init__(identifier)
        self.__name = None
        self.__email = None
        self.__phone = None
        self.__document = None
        self.name = name
        self.email = email
        self.phone = phone
        self.document = document
        EventLogger.log_event("Cliente creado", {"id": identifier, "name": name})

    def __str__(self) -> str:
        return f"Cliente({self.identifier}, {self.name}, {self.email})"

    @property
    def name(self) -> str:
        return self.__name

    @name.setter
    def name(self, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ClientRegistrationError("El nombre del cliente no puede estar vacío.")
        self.__name = value.strip()

    @property
    def email(self) -> str:
        return self.__email

    @email.setter
    def email(self, value: str) -> None:
        if not isinstance(value, str) or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value):
            raise ClientRegistrationError("Correo electrónico inválido.")
        self.__email = value.strip()

    @property
    def phone(self) -> str:
        return self.__phone

    @phone.setter
    def phone(self, value: str) -> None:
        normalized = re.sub(r"\D", "", value or "")
        if len(normalized) < 7:
            raise ClientRegistrationError("Teléfono inválido.")
        self.__phone = normalized

    @property
    def document(self) -> str:
        return self.__document

    @document.setter
    def document(self, value: str) -> None:
        if not isinstance(value, str) or len(value.strip()) < 5:
            raise ClientRegistrationError("Documento inválido.")
        self.__document = value.strip()

    def describe(self) -> str:
        return f"Cliente {self.name} ({self.document})"


class Service(ABC):
    """Clase abstracta de servicio con polimorfismo y validaciones."""

    def __init__(self, service_id: str, base_cost: float) -> None:
        self.service_id = service_id
        self.base_cost = base_cost
        self.validate_parameters()

    @abstractmethod
    def calculate_cost(self, tax_rate: float = 0.0, discount: float = 0.0, include_insurance: bool = False) -> float:
        pass

    @abstractmethod
    def describe(self) -> str:
        pass

    @abstractmethod
    def validate_parameters(self) -> None:
        pass

    def _apply_tax_and_discount(self, amount: float, tax_rate: float, discount: float) -> float:
        if tax_rate < 0 or discount < 0:
            raise CostCalculationError("El impuesto o descuento no puede ser negativo.")
        cost = amount + amount * tax_rate - amount * discount
        return round(cost, 2)


class RoomReservation(Service):
    """Servicio de reserva de salas."""

    VALID_ROOM_TYPES = {"pequeña": 50.0, "mediana": 100.0, "grande": 180.0}

    def __init__(self, service_id: str, room_type: str, duration_hours: int, attendees: int) -> None:
        self.room_type = room_type
        self.duration_hours = duration_hours
        self.attendees = attendees
        super().__init__(service_id, self.VALID_ROOM_TYPES.get(room_type.lower(), 0.0))

    def validate_parameters(self) -> None:
        if self.room_type.lower() not in self.VALID_ROOM_TYPES:
            raise ServiceUnavailableError(f"Tipo de sala no disponible: {self.room_type}")
        if self.duration_hours <= 0:
            raise ServiceUnavailableError("La duración de la reserva debe ser mayor a 0.")
        if self.attendees <= 0:
            raise ServiceUnavailableError("Debe haber al menos un asistente.")

    def describe(self) -> str:
        return f"Reserva de sala {self.room_type} por {self.duration_hours}h para {self.attendees} asistentes"

    def calculate_cost(self, tax_rate: float = 0.0, discount: float = 0.0, include_insurance: bool = False) -> float:
        base = self.base_cost * self.duration_hours
        if self.attendees > 20:
            base += 100.0
        if include_insurance:
            base += 30.0
        return self._apply_tax_and_discount(base, tax_rate, discount)


class EquipmentRental(Service):
    """Servicio de alquiler de equipos."""

    VALID_EQUIPMENT = {"proyector": 80.0, "cámara": 120.0, "computadora": 150.0}

    def __init__(self, service_id: str, equipment_type: str, quantity: int, rental_days: int) -> None:
        self.equipment_type = equipment_type
        self.quantity = quantity
        self.rental_days = rental_days
        base_cost = self.VALID_EQUIPMENT.get(equipment_type.lower(), 0.0)
        super().__init__(service_id, base_cost)

    def validate_parameters(self) -> None:
        if self.equipment_type.lower() not in self.VALID_EQUIPMENT:
            raise ServiceUnavailableError(f"Equipo no disponible: {self.equipment_type}")
        if self.quantity <= 0:
            raise ServiceUnavailableError("La cantidad de equipos debe ser positiva.")
        if self.rental_days <= 0:
            raise ServiceUnavailableError("Los días de alquiler deben ser mayores a 0.")

    def describe(self) -> str:
        return f"Alquiler de {self.quantity} {self.equipment_type}(s) por {self.rental_days} días"

    def calculate_cost(self, tax_rate: float = 0.0, discount: float = 0.0, include_insurance: bool = False) -> float:
        base = self.base_cost * self.quantity * self.rental_days
        if self.quantity >= 5:
            discount += 0.05
        if include_insurance:
            base += 20.0 * self.quantity
        return self._apply_tax_and_discount(base, tax_rate, discount)


class SpecializedAdvisory(Service):
    """Servicio de asesoría especializada."""

    EXPERT_LEVEL_MULTIPLIER = {"junior": 1.0, "senior": 1.5, "experto": 2.0}

    def __init__(self, service_id: str, topic: str, specialist_level: str, hours: int) -> None:
        self.topic = topic
        self.specialist_level = specialist_level
        self.hours = hours
        multiplier = self.EXPERT_LEVEL_MULTIPLIER.get(specialist_level.lower(), 1.0)
        super().__init__(service_id, 120.0 * multiplier)

    def validate_parameters(self) -> None:
        if not self.topic or not isinstance(self.topic, str):
            raise ServiceUnavailableError("El tema de asesoría no puede estar vacío.")
        if self.specialist_level.lower() not in self.EXPERT_LEVEL_MULTIPLIER:
            raise ServiceUnavailableError(f"Nivel de especialista inválido: {self.specialist_level}")
        if self.hours <= 0:
            raise ServiceUnavailableError("Las horas de asesoría deben ser mayores a 0.")

    def describe(self) -> str:
        return f"Asesoría en {self.topic} con especialista {self.specialist_level} por {self.hours}h"

    def calculate_cost(self, tax_rate: float = 0.0, discount: float = 0.0, include_insurance: bool = False) -> float:
        if self.hours > 8:
            discount += 0.10
        base = self.base_cost * self.hours
        if include_insurance:
            base += 40.0
        return self._apply_tax_and_discount(base, tax_rate, discount)


class Reservation:
    """Gestiona reservas de clientes con servicio, estado y excepciones."""

    VALID_STATES = {"pendiente", "confirmada", "cancelada", "procesada"}

    def __init__(self, reservation_id: str, client: Client, service: Service) -> None:
        self.reservation_id = reservation_id
        self.client = client
        self.service = service
        self.state = "pendiente"
        self.created_at = datetime.utcnow()
        EventLogger.log_event("Reserva creada", {"reservation_id": reservation_id, "client_id": client.identifier, "service_id": service.service_id})

    def confirm(self) -> None:
        if self.state == "cancelada":
            raise ReservationError("No se puede confirmar una reserva cancelada.")
        if self.state == "confirmada":
            raise ReservationError("La reserva ya está confirmada.")
        self.state = "confirmada"
        EventLogger.log_event("Reserva confirmada", {"reservation_id": self.reservation_id})

    def cancel(self) -> None:
        if self.state == "cancelada":
            raise ReservationError("La reserva ya está cancelada.")
        if self.state == "procesada":
            raise ReservationError("No se puede cancelar una reserva procesada.")
        self.state = "cancelada"
        EventLogger.log_event("Reserva cancelada", {"reservation_id": self.reservation_id})

    def process(self, tax_rate: float = 0.0, discount: float = 0.0, include_insurance: bool = False) -> float:
        try:
            if self.state == "cancelada":
                raise ReservationError("No se puede procesar una reserva cancelada.")
            if self.state == "pendiente":
                raise ReservationError("La reserva debe confirmarse antes de procesar.")
            cost = self.service.calculate_cost(tax_rate, discount, include_insurance)
            if cost <= 0:
                raise CostCalculationError("El costo calculado no puede ser cero o negativo.")
        except Exception as err:
            EventLogger.log_error(err, {"reservation_id": self.reservation_id, "state": self.state})
            raise
        else:
            self.state = "procesada"
            EventLogger.log_event("Reserva procesada", {"reservation_id": self.reservation_id, "total_cost": cost})
            return cost
        finally:
            EventLogger.log_event("Intento de proceso de reserva", {"reservation_id": self.reservation_id, "state": self.state})

    def describe(self) -> str:
        return f"Reserva {self.reservation_id}: {self.client.describe()} - {self.service.describe()} [{self.state}]"
