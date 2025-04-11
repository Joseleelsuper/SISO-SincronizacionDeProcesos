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
NUM_PRODUCERS = 1
NUM_CONSUMERS = 3


class ProducerConsumer:
    """
    Monitor que implementa la solución al problema del productor-consumidor.
    Gestiona un buffer compartido con acceso sincronizado.
    """

    def __init__(self, buffer_size: int = BUFFER_SIZE):
        """Inicializa el monitor productor-consumidor.
        Crea un buffer compartido y establece su tamaño máximo.

        Args:
            buffer_size (int, optional): Tamaño del Búffer de objetos. Defaults to BUFFER_SIZE.
        """
        self.buffer = []
        self.buffer_size = buffer_size
        self.condition = threading.Condition()

    def produce(self, item: int, producer_id: int, color: str):
        """Añade un item al buffer. Se bloquea si el buffer está lleno.

        Args:
            item (int): Ítem a añadir al buffer.
            producer_id (int): ID del productor que produce el item.
            color (str): Color del productor para imprimir mensajes en la consola.
        """
        with self.condition:
            # Esperar mientras el buffer esté lleno
            while len(self.buffer) >= self.buffer_size:
                print(f"{color}Productor {producer_id} esperando, buffer lleno{RESET}")
                self.condition.wait()

            # Añadir el item al buffer
            self.buffer.append(item)
            print(
                f"{color}Productor {producer_id} añade el item {item}. Buffer: {self.buffer}{RESET}"
            )

            # Notificar a los consumidores que pueden consumir
            self.condition.notify_all()

    def consume(self, consumer_id: int, color: str) -> int:
        """Extrae un item del buffer. Se bloquea si el buffer está vacío.

        Args:
            consumer_id (int): ID del consumidor que consume el item.
            color (str): Color del consumidor para imprimir mensajes en la consola.

        Returns:
            int: Ítem extraído del buffer.
        """
        with self.condition:
            # Esperar mientras el buffer esté vacío
            while len(self.buffer) == 0:
                print(f"{color}Consumidor {consumer_id} esperando, buffer vacío{RESET}")
                self.condition.wait()

            # Extraer un item del buffer
            item = self.buffer.pop(0)
            print(
                f"{color}Consumidor {consumer_id} extrae el item {item}. Buffer: {self.buffer}{RESET}"
            )

            # Notificar a los productores que pueden producir
            self.condition.notify_all()

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
    """Hilo productor que genera items y los coloca en el buffer compartido.
    """

    def __init__(
        self,
        producer_id: int,
        producer_consumer: ProducerConsumer,
        color: str,
        min_production_time: int = MIN_PRODUCTION_TIME,
        max_production_time: int = MAX_PRODUCTION_TIME,
    ):
        """Inicializa un productor con un ID, un monitor productor-consumidor y un color para imprimir mensajes.
        Esto permite que cada productor actúe de manera independiente y se sincronice con los consumidores a través del monitor.

        Args:
            producer_id (int): ID del productor.
            producer_consumer (ProducerConsumer): Instancia del monitor productor-consumidor.
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
    """Hilo consumidor que extrae y procesa items del buffer compartido.
    """

    def __init__(
        self,
        consumer_id: int,
        producer_consumer: ProducerConsumer,
        color: str,
        min_consumption_time: int = MIN_CONSUMPTION_TIME,
        max_consumption_time: int = MAX_CONSUMPTION_TIME,
    ):
        """Inicializa un consumidor con un ID, un monitor productor-consumidor y un color para imprimir mensajes.
        Esto permite que cada consumidor actúe de manera independiente y se sincronice con los productores a través del monitor.

        Args:
            consumer_id (int): ID del consumidor.
            producer_consumer (ProducerConsumer): Instancia del monitor productor-consumidor.
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
    Crea instancias de productores y consumidores, y las inicia como hilos.
    Cada productor genera items y los coloca en el buffer, mientras que cada consumidor extrae y procesa items del buffer.
    La simulación continúa indefinidamente hasta que se interrumpe manualmente.
    """
    # Crear instancia de ProducerConsumer
    producer_consumer = ProducerConsumer(BUFFER_SIZE)

    # Crear varios productores
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
