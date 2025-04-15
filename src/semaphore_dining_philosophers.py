import threading
import time
import random

try:
    from src.utils.colors import COLORS, RESET
except ImportError:
    from utils.colors import COLORS, RESET

# Tiempos de pensamiento y comida
MINIMUM_THINKING_TIME = 7
MAXIMUM_THINKING_TIME = 15
MINIMUM_EATING_TIME = 5
MAXIMUM_EATING_TIME = 10

# Estado de los tenedores
FORK_STATES = ["free", "taken"]


class SemaphoreDiningPhilosophers:
    """
    Implementación del problema de los filósofos comensales utilizando semáforos.
    Gestiona el acceso a los tenedores mediante semáforos para evitar deadlocks y condiciones de carrera.
    """

    def __init__(self, number_of_philosophers: int = 5):
        """
        Inicializa los semáforos para los tenedores y crea los filósofos.

        Args:
            number_of_philosophers (int, optional): Número de filósofos en la simulación. Defaults to 5.
        """
        self.number_of_philosophers = number_of_philosophers
        self.philosophers = []
        self.fork_state = [FORK_STATES[0]] * number_of_philosophers

        # Crear un semáforo para cada tenedor
        self.forks = [threading.Semaphore(1) for _ in range(number_of_philosophers)]

        # Mutex para proteger el acceso a fork_state (solo para mostrar el estado)
        self.mutex = threading.Semaphore(1)

        # Crear los filósofos
        for i in range(number_of_philosophers):
            philosopher = Philosopher(i, self, COLORS[i % len(COLORS)])
            self.philosophers.append(philosopher)

    def pickup_forks(self, philosopher_id: int, color: str):
        """
        Permite a un filósofo tomar los tenedores que necesita para comer.
        Utiliza semáforos para garantizar acceso exclusivo a cada tenedor.

        Args:
            philosopher_id (int): ID del filósofo que quiere comer.
            color (str): Color del filósofo para imprimir mensajes en la consola.
        """
        # Estrategia: para evitar deadlocks, tomamos primero el tenedor con índice menor
        left_fork = philosopher_id
        right_fork = (philosopher_id + 1) % self.number_of_philosophers

        # Asegurar que tomamos primero el tenedor con índice menor
        first_fork = min(left_fork, right_fork)
        second_fork = max(left_fork, right_fork)

        print(
            f"{color}Filósofo {philosopher_id} quiere tomar tenedores {left_fork} y {right_fork}{RESET}"
        )

        # Adquirir el primer tenedor
        self.forks[first_fork].acquire()
        # Actualizar el estado del tenedor (solo para mostrar)
        self.mutex.acquire()
        self.fork_state[first_fork] = FORK_STATES[1]
        self.mutex.release()
        print(f"{color}Filósofo {philosopher_id} toma tenedor {first_fork}{RESET}")

        # Adquirir el segundo tenedor solo si es diferente del primero
        if first_fork != second_fork:  # Esto evita el bloqueo con un solo filósofo
            self.forks[second_fork].acquire()
            # Actualizar el estado del tenedor (solo para mostrar)
            self.mutex.acquire()
            self.fork_state[second_fork] = FORK_STATES[1]
            self.mutex.release()
            print(f"{color}Filósofo {philosopher_id} toma tenedor {second_fork}{RESET}")

        print(
            f"{color}Filósofo {philosopher_id} tiene ambos tenedores y comienza a comer{RESET}"
        )

    def putdown_forks(self, philosopher_id: int, color: str):
        """
        Permite a un filósofo soltar los tenedores después de comer.
        Libera los semáforos para que otros filósofos puedan usarlos.

        Args:
            philosopher_id (int): ID del filósofo que quiere liberar los tenedores.
            color (str): Color del filósofo para imprimir mensajes en la consola.
        """
        left_fork = philosopher_id
        right_fork = (philosopher_id + 1) % self.number_of_philosophers

        # Para garantizar consistencia con pickup_forks
        first_fork = min(left_fork, right_fork)
        second_fork = max(left_fork, right_fork)

        # Liberar el primer tenedor
        self.mutex.acquire()
        self.fork_state[first_fork] = FORK_STATES[0]
        self.mutex.release()
        self.forks[first_fork].release()
        print(f"{color}Filósofo {philosopher_id} suelta tenedor {first_fork}{RESET}")

        # Liberar el segundo tenedor solo si es diferente del primero
        if first_fork != second_fork:  # Esto evita liberar dos veces el mismo semáforo
            self.mutex.acquire()
            self.fork_state[second_fork] = FORK_STATES[0]
            self.mutex.release()
            self.forks[second_fork].release()
            print(f"{color}Filósofo {philosopher_id} suelta tenedor {second_fork}{RESET}")

        print(
            f"{color}Filósofo {philosopher_id} terminó de comer y liberó ambos tenedores{RESET}"
        )


class Philosopher(threading.Thread):
    """
    Clase que representa a un filósofo en el problema de los filósofos comensales.
    Cada filósofo es un hilo que alterna entre pensar y comer.
    """

    def __init__(
        self,
        philosopher_id: int,
        dining_philosophers: SemaphoreDiningPhilosophers,
        color: str,
    ):
        """
        Inicializa un filósofo con un ID, un gestor de semáforos y un color para imprimir mensajes.

        Args:
            philosopher_id (int): ID del filósofo.
            dining_philosophers (SemaphoreDiningPhilosophers): Instancia del gestor de semáforos para filósofos.
            color (str): Color del filósofo para imprimir mensajes en la consola.
        """
        threading.Thread.__init__(self)
        self.philosopher_id = philosopher_id
        self.dining_philosophers = dining_philosophers
        self.color = color
        self.daemon = True

    def run(self):
        """Ejecuta de manera indefinida el ciclo de pensar y comer."""
        while True:
            self.think()
            self.eat()

    def think(self):
        """Simula el proceso de pensar por un tiempo aleatorio."""
        thinking_time = random.randint(MINIMUM_THINKING_TIME, MAXIMUM_THINKING_TIME)
        print(
            f"{self.color}Filósofo {self.philosopher_id} está pensando durante {thinking_time} segundos{RESET}"
        )
        time.sleep(thinking_time)

    def eat(self):
        """Simula el proceso de comer."""
        print(
            f"{self.color}Filósofo {self.philosopher_id} tiene hambre y quiere comer{RESET}"
        )
        self.dining_philosophers.pickup_forks(self.philosopher_id, self.color)

        eating_time = random.randint(MINIMUM_EATING_TIME, MAXIMUM_EATING_TIME)
        print(
            f"{self.color}Filósofo {self.philosopher_id} está comiendo durante {eating_time} segundos{RESET}"
        )
        time.sleep(eating_time)

        self.dining_philosophers.putdown_forks(self.philosopher_id, self.color)


def main():
    """
    Función principal para iniciar la simulación de los filósofos comensales.
    Crea una instancia del gestor de semáforos y lanza los hilos de los filósofos.
    Cada filósofo alterna entre pensar y comer, utilizando semáforos para coordinar el acceso a los tenedores.
    """
    dining_philosophers = SemaphoreDiningPhilosophers()

    # Iniciar todos los hilos de filósofos
    for philosopher in dining_philosophers.philosophers:
        philosopher.start()

    # Mantener vivo el hilo principal
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Simulación terminada por el usuario")


if __name__ == "__main__":
    main()
