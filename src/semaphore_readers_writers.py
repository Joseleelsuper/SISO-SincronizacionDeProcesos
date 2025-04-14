import threading
import time
import random
from abc import ABC

try:
    from src.utils.colors import COLORS, RESET
except ImportError:
    from utils.colors import COLORS, RESET

# Tiempos de lectura y escritura
MIN_READING_TIME = 2
MAX_READING_TIME = 5
MIN_WRITING_TIME = 3
MAX_WRITING_TIME = 7

# Número de lectores y escritores
NUM_READERS = 5
NUM_READERS = 2

# Estados del recurso compartido
RESOURCE_STATES = ["free", "reading", "writing"]


class SemaphoreReadersWriters:
    """
    Implementación del problema de los lectores y escritores utilizando semáforos.
    Gestiona el acceso a un recurso compartido entre lectores y escritores.
    """

    def __init__(self):
        """
        Inicializa la estructura de datos y los semáforos necesarios.
        """
        # Estado inicial del recurso
        self.resource_state = RESOURCE_STATES[0]  # Estado inicial: libre
        self.readers_count = 0  # Contador de lectores activos
        self.resource_content = "Contenido inicial del recurso"  # Contenido del recurso compartido
        
        # Semáforos para sincronización
        self.mutex = threading.Semaphore(1)  # Para proteger la modificación del contador de lectores
        self.write_lock = threading.Semaphore(1)  # Para acceso exclusivo al recurso para escritores
        self.resource_mutex = threading.Semaphore(1)  # Para actualizar el estado del recurso

    def start_read(self, reader_id: int, color: str):
        """
        Permite que un lector comience a leer el recurso.
        Se bloquea si hay un escritor activo.

        Args:
            reader_id (int): ID del lector.
            color (str): Color del lector para imprimir mensajes en la consola.
        """
        print(f"{color}Lector {reader_id} quiere leer{RESET}")
        
        # Esperar si hay un escritor
        self.mutex.acquire()
        
        try:
            self.readers_count += 1
            if self.readers_count == 1:  # Primer lector
                # Bloquear el recurso para escritores
                self.write_lock.acquire()
                
                # Actualizar el estado del recurso
                self.resource_mutex.acquire()
                self.resource_state = RESOURCE_STATES[1]  # Estado: leyendo
                self.resource_mutex.release()
        finally:
            self.mutex.release()
            
        print(f"{color}Lector {reader_id} comienza a leer. Lectores activos: {self.readers_count}{RESET}")

    def end_read(self, reader_id: int, color: str):
        """
        Permite que un lector termine de leer el recurso.
        Libera el recurso para escritores si es el último lector.

        Args:
            reader_id (int): ID del lector.
            color (str): Color del lector para imprimir mensajes en la consola.
        """
        self.mutex.acquire()
        
        try:
            self.readers_count -= 1
            if self.readers_count == 0:  # Último lector
                # Liberar el recurso para escritores
                
                # Actualizar el estado del recurso
                self.resource_mutex.acquire()
                self.resource_state = RESOURCE_STATES[0]  # Estado: libre
                self.resource_mutex.release()
                
                self.write_lock.release()
        finally:
            self.mutex.release()
            
        print(f"{color}Lector {reader_id} termina de leer. Lectores activos: {self.readers_count}{RESET}")

    def start_write(self, writer_id: int, color: str):
        """
        Permite que un escritor comience a escribir en el recurso.
        Se bloquea si hay lectores activos o si otro escritor está activo.

        Args:
            writer_id (int): ID del escritor.
            color (str): Color del escritor para imprimir mensajes en la consola.
        """
        print(f"{color}Escritor {writer_id} quiere escribir{RESET}")
        
        # Esperar acceso exclusivo al recurso
        self.write_lock.acquire()
        
        # Actualizar el estado del recurso
        self.resource_mutex.acquire()
        self.resource_state = RESOURCE_STATES[2]  # Estado: escribiendo
        self.resource_mutex.release()
        
        print(f"{color}Escritor {writer_id} comienza a escribir{RESET}")

    def end_write(self, writer_id: int, color: str, new_content: str):
        """
        Permite que un escritor termine de escribir en el recurso.
        Actualiza el contenido del recurso y lo libera.

        Args:
            writer_id (int): ID del escritor.
            color (str): Color del escritor para imprimir mensajes en la consola.
            new_content (str): Nuevo contenido para el recurso compartido.
        """
        # Actualizar el contenido y el estado del recurso
        self.resource_mutex.acquire()
        self.resource_content = new_content
        self.resource_state = RESOURCE_STATES[0]  # Estado: libre
        self.resource_mutex.release()
        
        # Liberar el recurso
        self.write_lock.release()
        
        print(f"{color}Escritor {writer_id} termina de escribir. Nuevo contenido: {self.resource_content}{RESET}")

    def read_resource(self, reader_id: int, color: str) -> str:
        """
        Permite a un lector acceder al contenido del recurso.

        Args:
            reader_id (int): ID del lector.
            color (str): Color del lector para imprimir mensajes en la consola.

        Returns:
            str: Contenido del recurso compartido.
        """
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
        readers_writers: SemaphoreReadersWriters,
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
        readers_writers: SemaphoreReadersWriters,
        color: str,
        min_reading_time: int = MIN_READING_TIME,
        max_reading_time: int = MAX_READING_TIME,
        min_thinking_time: int = 2,
        max_thinking_time: int = 5,
    ):
        """
        Inicializa un lector con un ID, un gestor de semáforos y un color para imprimir mensajes.
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
        readers_writers: SemaphoreReadersWriters,
        color: str,
        min_writing_time: int = MIN_WRITING_TIME,
        max_writing_time: int = MAX_WRITING_TIME,
        min_thinking_time: int = 3,
        max_thinking_time: int = 8,
    ):
        """
        Inicializa un escritor con un ID, un gestor de semáforos y un color para imprimir mensajes.
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
    Crea una instancia del gestor de semáforos y lanza los hilos de lectores y escritores.
    """
    # Crear el gestor de semáforos para lectores y escritores
    readers_writers = SemaphoreReadersWriters()

    # Crear lectores
    readers = []
    for i in range(NUM_READERS):
        reader = Reader(i, readers_writers, COLORS[i % len(COLORS)])
        readers.append(reader)

    # Crear escritores
    writers = []
    for i in range(NUM_READERS):
        writer = Writer(i, readers_writers, COLORS[(i + NUM_READERS) % len(COLORS)])
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
