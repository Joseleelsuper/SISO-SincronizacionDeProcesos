from abc import ABC
import threading
import time
import random

try:
    from src.utils.colors import COLORS, RESET
except ImportError:
    from utils.colors import COLORS, RESET

# Tiempos de lectura y escritura
MIN_READING_TIME = 2
MAX_READING_TIME = 5
MIN_WRITING_TIME = 3
MAX_WRITING_TIME = 7

# Estados del recurso compartido
RESOURCE_STATES = ["free", "reading", "writing"]


class ReadersWriters:
    """
    Monitor que implementa la solución al problema de los lectores y escritores.
    Gestiona el acceso a un recurso compartido entre lectores y escritores.
    """

    def __init__(self):
        """
        Inicializa el monitor de lectores y escritores.
        Establece el estado inicial del recurso y los contadores de lectores y escritores.
        """
        self.resource_state = RESOURCE_STATES[0]  # Estado inicial: libre
        self.readers_count = 0  # Contador de lectores activos
        self.writers_waiting = 0  # Contador de escritores en espera
        self.active_writer = False  # Indica si hay un escritor activo
        self.condition = threading.Condition()  # Condición para sincronización
        self.resource_content = (
            "Contenido inicial del recurso"  # Contenido del recurso compartido
        )

    def start_read(self, reader_id: int, color: str):
        """
        Permite que un lector comience a leer el recurso.
        Se bloquea si hay un escritor activo o en espera.

        Args:
            reader_id (int): ID del lector.
            color (str): Color del lector para imprimir mensajes en la consola.
        """
        with self.condition:
            # Esperar si hay un escritor activo o escritores en espera
            while self.active_writer or self.writers_waiting > 0:
                print(
                    f"{color}Lector {reader_id} esperando, hay escritor activo o en espera{RESET}"
                )
                self.condition.wait()

            # Incrementar el contador de lectores
            self.readers_count += 1

            # Cambiar el estado del recurso a lectura
            if self.resource_state == RESOURCE_STATES[0]:  # Si estaba libre
                self.resource_state = RESOURCE_STATES[1]  # Cambiar a estado de lectura

            print(
                f"{color}Lector {reader_id} comienza a leer. Lectores activos: {self.readers_count}{RESET}"
            )

    def end_read(self, reader_id: int, color: str):
        """
        Permite que un lector termine de leer el recurso.
        Notifica a los escritores en espera si no hay más lectores.

        Args:
            reader_id (int): ID del lector.
            color (str): Color del lector para imprimir mensajes en la consola.
        """
        with self.condition:
            # Decrementar el contador de lectores
            self.readers_count -= 1

            print(
                f"{color}Lector {reader_id} termina de leer. Lectores activos: {self.readers_count}{RESET}"
            )

            # Si no hay más lectores, cambiar el estado del recurso a libre
            if self.readers_count == 0:
                self.resource_state = RESOURCE_STATES[0]  # Cambiar a estado libre
                # Notificar a todos los procesos en espera
                self.condition.notify_all()

    def start_write(self, writer_id: int, color: str):
        """
        Permite que un escritor comience a escribir en el recurso.
        Se bloquea si hay lectores activos o si otro escritor está activo.

        Args:
            writer_id (int): ID del escritor.
            color (str): Color del escritor para imprimir mensajes en la consola.
        """
        with self.condition:
            # Incrementar el contador de escritores en espera
            self.writers_waiting += 1

            # Esperar si hay lectores activos o otro escritor activo
            while self.readers_count > 0 or self.active_writer:
                print(
                    f"{color}Escritor {writer_id} esperando, hay lectores activos o un escritor activo{RESET}"
                )
                self.condition.wait()

            # Decrementar el contador de escritores en espera
            self.writers_waiting -= 1

            # Marcar que hay un escritor activo
            self.active_writer = True

            # Cambiar el estado del recurso a escritura
            self.resource_state = RESOURCE_STATES[2]

            print(f"{color}Escritor {writer_id} comienza a escribir{RESET}")

    def end_write(self, writer_id: int, color: str, new_content: str):
        """
        Permite que un escritor termine de escribir en el recurso.
        Actualiza el contenido del recurso y notifica a los procesos en espera.

        Args:
            writer_id (int): ID del escritor.
            color (str): Color del escritor para imprimir mensajes en la consola.
            new_content (str): Nuevo contenido para el recurso compartido.
        """
        with self.condition:
            # Actualizar el contenido del recurso
            self.resource_content = new_content

            # Marcar que no hay un escritor activo
            self.active_writer = False

            # Cambiar el estado del recurso a libre
            self.resource_state = RESOURCE_STATES[0]

            print(
                f"{color}Escritor {writer_id} termina de escribir. Nuevo contenido: {self.resource_content}{RESET}"
            )

            # Notificar a todos los procesos en espera
            self.condition.notify_all()

    def read_resource(self, reader_id: int, color: str) -> str:
        """
        Permite a un lector acceder al contenido del recurso.

        Args:
            reader_id (int): ID del lector.
            color (str): Color del lector para imprimir mensajes en la consola.

        Returns:
            str: Contenido del recurso compartido.
        """
        with self.condition:
            content = self.resource_content
            print(f"{color}Lector {reader_id} leyó: {content}{RESET}")
            return content


class People(ABC, threading.Thread):
    """
    Clase base para los hilos de lectores y escritores.
    Define la estructura básica de un hilo en el problema de los lectores y escritores.
    """

    def __init__(
        self,
        id: int,
        readers_writers: ReadersWriters,
        color: str,
        min_time: int,
        max_time: int,
        min_thinking_time: int,
        max_thinking_time: int,
    ):
        """
        Inicializa un hilo de lector o escritor.
        """
        threading.Thread.__init__(self)
        self.id = id
        self.readers_writers = readers_writers
        self.color = color
        self.min_time = min_time
        self.max_time = max_time
        self.min_thinking_time = min_thinking_time
        self.max_thinking_time = max_thinking_time
        self.daemon = True  # Hilo daemon para que termine al cerrar el programa

    def run(self) -> None:
        """Método abstracto que debe ser implementado por las subclases."""
        pass


class Reader(People):
    """
    Clase que representa a un lector en el problema de los lectores y escritores.
    Cada lector es un hilo que intenta leer el recurso compartido.
    """

    def __init__(
        self,
        reader_id: int,
        readers_writers: ReadersWriters,
        color: str,
        min_reading_time: int = MIN_READING_TIME,
        max_reading_time: int = MAX_READING_TIME,
        min_thinking_time: int = 2,
        max_thinking_time: int = 5,
    ):
        """
        Inicializa un lector con un ID, un monitor de lectores y escritores y un color para imprimir mensajes.
        """
        super().__init__(
            reader_id,
            readers_writers,
            color,
            min_reading_time,
            max_reading_time,
            min_thinking_time,
            max_thinking_time,
        )
        self.reader_id = reader_id

    def run(self):
        """Ejecuta el ciclo de lectura del recurso compartido."""
        while True:
            # Tiempo de espera antes de intentar leer
            think_time = random.randint(self.min_thinking_time, self.max_thinking_time)
            print(
                f"{self.color}Lector {self.reader_id} pensando durante {think_time} segundos{RESET}"
            )
            time.sleep(think_time)

            # Comenzar a leer
            self.readers_writers.start_read(self.reader_id, self.color)
            self.readers_writers.read_resource(self.reader_id, self.color)

            # Simular tiempo de lectura
            reading_time = random.randint(self.min_time, self.max_time)
            print(
                f"{self.color}Lector {self.reader_id} leyendo durante {reading_time} segundos{RESET}"
            )
            time.sleep(reading_time)

            # Terminar la lectura
            self.readers_writers.end_read(self.reader_id, self.color)


class Writer(People):
    """
    Clase que representa a un escritor en el problema de los lectores y escritores.
    Cada escritor es un hilo que intenta escribir en el recurso compartido.
    """

    def __init__(
        self,
        writer_id: int,
        readers_writers: ReadersWriters,
        color: str,
        min_writing_time: int = MIN_WRITING_TIME,
        max_writing_time: int = MAX_WRITING_TIME,
        min_thinking_time: int = 3,
        max_thinking_time: int = 8,
    ):
        """
        Inicializa un escritor con un ID, un monitor de lectores y escritores y un color para imprimir mensajes.
        """
        super().__init__(
            writer_id,
            readers_writers,
            color,
            min_writing_time,
            max_writing_time,
            min_thinking_time,
            max_thinking_time,
        )
        self.writer_id = writer_id

    def run(self):
        """Ejecuta el ciclo de escritura en el recurso compartido."""
        while True:
            # Tiempo de espera antes de intentar escribir
            think_time = random.randint(self.min_thinking_time, self.max_thinking_time)
            print(
                f"{self.color}Escritor {self.writer_id} pensando durante {think_time} segundos{RESET}"
            )
            time.sleep(think_time)

            # Comenzar a escribir
            self.readers_writers.start_write(self.writer_id, self.color)

            # Simular tiempo de escritura
            writing_time = random.randint(self.min_time, self.max_time)
            print(
                f"{self.color}Escritor {self.writer_id} escribiendo durante {writing_time} segundos{RESET}"
            )
            time.sleep(writing_time)

            # Generar nuevo contenido
            new_content = (
                f"Contenido escrito por Escritor {self.writer_id} en {time.time()}"
            )

            # Terminar la escritura con el nuevo contenido
            self.readers_writers.end_write(self.writer_id, self.color, new_content)


def main():
    """
    Función principal para iniciar la simulación de los lectores y escritores.
    Crea una instancia del monitor de lectores y escritores y lanza los hilos de lectores y escritores.
    """
    # Crear el monitor de lectores y escritores
    readers_writers = ReadersWriters()

    # Número de lectores y escritores
    num_readers = 5
    num_writers = 2

    # Crear lectores
    readers = []
    for i in range(num_readers):
        reader = Reader(i, readers_writers, COLORS[i % len(COLORS)])
        readers.append(reader)

    # Crear escritores
    writers = []
    for i in range(num_writers):
        writer = Writer(i, readers_writers, COLORS[(i + num_readers) % len(COLORS)])
        writers.append(writer)

    # Iniciar todos los hilos
    for thread in readers + writers:
        thread.start()

    # Mantener vivo el hilo principal
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Simulación terminada por el usuario")


if __name__ == "__main__":
    main()
