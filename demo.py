from software_fj import (
    Client,
    EquipmentRental,
    EventLogger,
    Reservation,
    RoomReservation,
    SpecializedAdvisory,
    ReservationError,
)


def run_demo() -> None:
    operations = []
    reservations = {}

    def attempt(operation_name: str, func):
        print(f"Ejecutando: {operation_name}")
        try:
            result = func()
            print("Resultado exitoso:", result)
            EventLogger.log_event("Operación exitosa", {"operation": operation_name})
            operations.append((operation_name, "exitoso", result))
        except Exception as err:
            print("Error controlado:", type(err).__name__, str(err))
            EventLogger.log_error(err, {"operation": operation_name})
            operations.append((operation_name, "fallido", str(err)))
        print("---")

    attempt("Crear cliente válido", lambda: Client("C001", "Ana Pérez", "ana.perez@ejemplo.com", "+34 612 345 678", "DNI12345"))
    attempt("Crear cliente sin email", lambda: Client("C002", "Carlos Ruiz", "", "612345678", "DNI54321"))
    attempt("Crear cliente con teléfono inválido", lambda: Client("C003", "Laura Soto", "laura.soto@ejemplo.com", "12", "DNI99887"))

    valid_client = Client("C004", "María López", "maria.lopez@ejemplo.com", "612 987 654", "DNI11122")

    attempt("Crear servicio de sala válido", lambda: RoomReservation("S001", "Mediana", 4, 12))
    attempt("Crear servicio de equipo inválido", lambda: EquipmentRental("S002", "drone", 2, 3))
    attempt("Crear asesoría especializada válida", lambda: SpecializedAdvisory("S003", "Ciberseguridad", "Experto", 6))

    room_service = RoomReservation("S004", "Grande", 3, 18)
    advisory_service = SpecializedAdvisory("S005", "Inteligencia Artificial", "Senior", 10)

    def create_and_confirm(reservation_id: str, client: Client, service) -> str:
        reservation = Reservation(reservation_id, client, service)
        reservation.confirm()
        reservations[reservation_id] = reservation
        return reservation.describe()

    def process_reservation(reservation_id: str, tax_rate: float, discount: float, include_insurance: bool) -> float:
        if reservation_id not in reservations:
            raise ReservationError(f"Reserva no encontrada: {reservation_id}")
        reservation = reservations[reservation_id]
        return reservation.process(tax_rate, discount, include_insurance)

    def create_and_cancel(reservation_id: str, client: Client, service) -> str:
        reservation = Reservation(reservation_id, client, service)
        reservation.cancel()
        reservations[reservation_id] = reservation
        return reservation.describe()

    def confirm_reservation(reservation_id: str) -> str:
        if reservation_id not in reservations:
            raise ReservationError(f"Reserva no encontrada: {reservation_id}")
        reservation = reservations[reservation_id]
        reservation.confirm()
        return reservation.describe()

    def create_reservation_with_invalid_service(reservation_id: str, client: Client):
        invalid_service = EquipmentRental("S006", "Cámara", -1, 5)
        reservation = Reservation(reservation_id, client, invalid_service)
        reservations[reservation_id] = reservation
        return reservation.describe()

    attempt("Crear y confirmar reserva válida", lambda: create_and_confirm("R001", valid_client, room_service))
    attempt("Procesar reserva con impuestos y seguro", lambda: process_reservation("R001", 0.16, 0.05, True))
    attempt("Crear y cancelar reserva", lambda: create_and_cancel("R002", valid_client, advisory_service))
    attempt("Procesar reserva cancelada", lambda: process_reservation("R002", 0.10, 0.0, False))
    attempt("Confirmar reserva cancelada", lambda: confirm_reservation("R002"))
    attempt("Crear reserva con servicio inválido", lambda: create_reservation_with_invalid_service("R003", valid_client))
    attempt("Calcular costo inconsistente", lambda: advisory_service.calculate_cost(tax_rate=-0.05, discount=0.0, include_insurance=False))

    print("Resumen de operaciones:")
    for op_name, status, detail in operations:
        print(f"- {op_name}: {status} -> {detail}")


if __name__ == "__main__":
    run_demo()
