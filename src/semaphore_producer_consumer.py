import threading
import time
import random
from abc import ABC, abstractmethod

try:
    from src.utils.colors import COLORS_CONSUMER, COLORS_PRODUCER, RESET
except ImportError:
    from utils.colors import COLORS_CONSUMER, COLORS_PRODUCER, RESET

# Tiempos de producción y consumo
MIN_PRODUCTION_TIME = 1
MAX_PRODUCTION_TIME = 3
MIN_CONSUMPTION_TIME = 2
MAX_CONSUMPTION_TIME = 5

# Tamaño del buffer
BUFFER_SIZE = 5

# Número de productores y consumidores
NUM_PRODUCERS = 3
NUM_CONSUMERS = 1


class SemaphoreProducerConsumer:
    """
    Implementación del problema del productor-consumidor utilizando semáforos.
    Gestiona un buffer compartido con acceso sincronizado mediante semáforos.
    """

    def __init__(self, buffer_size: int = BUFFER_SIZE):
        """Inicializa la estructura de datos y los semáforos.

        Args:
            buffer_size (int, optional): Tamaño del buffer. Defaults to BUFFER_SIZE.
        """
        self.buffer = []
        self.buffer_size = buffer_size

        # Semáforo para exclusión mutua
        self.mutex = threading.Semaphore(1)

        # Semáforo para controlar espacios vacíos
        self.empty = threading.Semaphore(buffer_size)

        # Semáforo para controlar espacios llenos
        self.filled = threading.Semaphore(0)

    def produce(self, item: int, producer_id: int, color: str):
        """Añade un item al buffer. Se bloquea si el buffer está lleno.

        Args:
            item (int): Ítem a añadir al buffer.
            producer_id (int): ID del productor que produce el item.
            color (str): Color del productor para imprimir mensajes en la consola.
        """
        # Esperar por un espacio vacío
        print(f"{color}Productor {producer_id} esperando espacio en el buffer{RESET}")
        self.empty.acquire()

        # Entrar a la sección crítica
        self.mutex.acquire()

        try:
            # Añadir el item al buffer
            self.buffer.append(item)
            print(
                f"{color}Productor {producer_id} añade el item {item}. Buffer: {self.buffer}{RESET}"
            )
        finally:
            # Salir de la sección crítica
            self.mutex.release()

        # Señalizar que hay un espacio lleno
        self.filled.release()

    def consume(self, consumer_id: int, color: str) -> int:
        """Extrae un item del buffer. Se bloquea si el buffer está vacío.

        Args:
            consumer_id (int): ID del consumidor que consume el item.
            color (str): Color del consumidor para imprimir mensajes en la consola.

        Returns:
            int: Ítem extraído del buffer.
        """
        # Esperar por un espacio lleno
        print(f"{color}Consumidor {consumer_id} esperando items en el buffer{RESET}")
        self.filled.acquire()

        # Entrar a la sección crítica
        self.mutex.acquire()

        try:
            # Extraer un item del buffer
            item = self.buffer.pop(0)
            print(
                f"{color}Consumidor {consumer_id} extrae el item {item}. Buffer: {self.buffer}{RESET}"
            )
        finally:
            # Salir de la sección crítica
            self.mutex.release()

        # Señalizar que hay un espacio vacío
        self.empty.release()

        return item


class Worker(threading.Thread, ABC):
    """Clase abstracta para los trabajadores (productores y consumidores).
    Define la estructura básica de un hilo productor o consumidor.
    """

    def __init__(
        self,
        worker_id,
        producer_consumer,
        color,
        min_time,
        max_time,
    ):
        super().__init__()
        self.worker_id = worker_id
        self.producer_consumer = producer_consumer
        self.color = color
        self.min_time = min_time
        self.max_time = max_time
        self.daemon = True

    def get_random_time(self) -> int:
        """Obtiene un tiempo aleatorio entre los límites configurados.

        Returns:
            int: Tiempo aleatorio entre min_time y max_time.
        """
        return random.randint(self.min_time, self.max_time)

    @abstractmethod
    def run(self): ...


class Producer(Worker):
    """Hilo productor que genera items y los coloca en el buffer compartido."""

    def __init__(
        self,
        producer_id: int,
        producer_consumer: SemaphoreProducerConsumer,
        color: str,
        min_production_time: int = MIN_PRODUCTION_TIME,
        max_production_time: int = MAX_PRODUCTION_TIME,
    ):
        """Inicializa un productor con un ID, un sistema productor-consumidor y un color para imprimir mensajes.
        Esto permite que cada productor actúe de manera independiente y se sincronice a través de los semáforos.

        Args:
            producer_id (int): ID del productor.
            producer_consumer (SemaphoreProducerConsumer): Instancia del sistema productor-consumidor.
            color (str): Color del productor para imprimir mensajes en la consola.
            min_production_time (int, optional): Tiempo mínimo de producción. Defaults to MIN_PRODUCTION_TIME.
            max_production_time (int, optional): Tiempo máximo de producción. Defaults to MAX_PRODUCTION_TIME.
        """
        super().__init__(
            producer_id,
            producer_consumer,
            color,
            min_production_time,
            max_production_time,
        )

    def run(self):
        item = 0
        while True:
            # Simular tiempo para producir un elemento
            production_time = self.get_random_time()
            print(
                f"{self.color}Productor {self.worker_id} produciendo durante {production_time} segundos{RESET}"
            )
            time.sleep(production_time)

            # Producir el elemento
            self.producer_consumer.produce(item, self.worker_id, self.color)
            item += 1


class Consumer(Worker):
    """Hilo consumidor que extrae y procesa items del buffer compartido."""

    def __init__(
        self,
        consumer_id: int,
        producer_consumer: SemaphoreProducerConsumer,
        color: str,
        min_consumption_time: int = MIN_CONSUMPTION_TIME,
        max_consumption_time: int = MAX_CONSUMPTION_TIME,
    ):
        """Inicializa un consumidor con un ID, un sistema productor-consumidor y un color para imprimir mensajes.
        Esto permite que el consumidor actúe de manera independiente y se sincronice a través de los semáforos.

        Args:
            consumer_id (int): ID del consumidor.
            producer_consumer (SemaphoreProducerConsumer): Instancia del sistema productor-consumidor.
            color (str): Color del consumidor para imprimir mensajes en la consola.
            min_consumption_time (int, optional): Tiempo mínimo de consumo. Defaults to MIN_CONSUMPTION_TIME.
            max_consumption_time (int, optional): Tiempo máximo de consumo. Defaults to MAX_CONSUMPTION_TIME.
        """
        super().__init__(
            consumer_id,
            producer_consumer,
            color,
            min_consumption_time,
            max_consumption_time,
        )

    def run(self):
        while True:
            # Consumir un elemento
            item = self.producer_consumer.consume(self.worker_id, self.color)

            # Simular tiempo para procesar el elemento
            consumption_time = self.get_random_time()
            print(
                f"{self.color}Consumidor {self.worker_id} procesando item {item} durante {consumption_time} segundos{RESET}"
            )
            time.sleep(consumption_time)


def main():
    """Función principal para iniciar la simulación del productor-consumidor.
    Crea instancias de productores y un consumidor, y las inicia como hilos.
    Cada productor genera items y los coloca en el buffer, mientras que el consumidor extrae y procesa items del buffer.
    La simulación continúa indefinidamente hasta que se interrumpe manualmente.
    """
    # Crear instancia de SemaphoreProducerConsumer
    producer_consumer = SemaphoreProducerConsumer(BUFFER_SIZE)

    producers = []
    for i in range(NUM_PRODUCERS):
        producer = Producer(
            i,
            producer_consumer,
            COLORS_PRODUCER[i % len(COLORS_PRODUCER)],
            MIN_PRODUCTION_TIME,
            MAX_PRODUCTION_TIME,
        )
        producers.append(producer)

    consumers = []
    for i in range(NUM_CONSUMERS):
        consumer = Consumer(
            i,
            producer_consumer,
            COLORS_CONSUMER[i % len(COLORS_CONSUMER)],
            MIN_CONSUMPTION_TIME,
            MAX_CONSUMPTION_TIME,
        )
        consumers.append(consumer)

    # Iniciar todos los hilos
    for worker in producers + consumers:
        worker.start()

    # Mantener vivo el hilo principal
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Simulación terminada por el usuario")


if __name__ == "__main__":
    main()
