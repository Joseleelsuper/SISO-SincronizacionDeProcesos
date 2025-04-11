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


class DiningPhilosophers:
    """Monitor para la solución del problema de los filósofos comensales.
    Este monitor controla el acceso a los tenedores y la sincronización entre los filósofos.
    """

    def __init__(self, number_of_philosophers=5):
        """Inicializa el monitor de filósofos comensales.
        Crea un número de filósofos y establece el estado inicial de los tenedores como libres.

        Args:
            number_of_philosophers (int, optional): Número de filósofos en la simulación. Defaults to 5.
        """
        self.number_of_philosophers = number_of_philosophers
        self.philosophers = []
        self.condition = threading.Condition()
        self.fork_state = [FORK_STATES[0]] * number_of_philosophers

        for i in range(number_of_philosophers):
            philosopher = Philosopher(i, self, COLORS[i % len(COLORS)])
            self.philosophers.append(philosopher)

    def pickup_forks(self, philosopher_id: int, color: str):
        """Permite que un filósofo tome los tenedores necesarios para comer.
        Utiliza un monitor para asegurar que los tenedores estén disponibles antes de permitir que el filósofo coma.
        Esto evita condiciones de carrera y asegura que los tenedores se manejen de manera segura.

        Args:
            philosopher_id (int): ID del filósofo que quiere comer.
            color (str): Color del filósofo para imprimir mensajes en la consola.
        """
        with self.condition:
            # Tenedor izquierdo y derecho del filósofo
            left_fork = philosopher_id
            right_fork = (philosopher_id + 1) % self.number_of_philosophers

            # Esperar hasta que ambos tenedores estén disponibles
            while (
                self.fork_state[left_fork] != FORK_STATES[0]
                or self.fork_state[right_fork] != FORK_STATES[0]
            ):
                print(
                    f"{color}Filósofo {philosopher_id} está esperando tenedores{RESET}"
                )
                self.condition.wait()

            # Tomar ambos tenedores
            self.fork_state[left_fork] = FORK_STATES[1]
            self.fork_state[right_fork] = FORK_STATES[1]
            print(
                f"{color}Filósofo {philosopher_id} toma tenedores {left_fork} y {right_fork}{RESET}"
            )

    def putdown_forks(self, philosopher_id: int, color: str):
        """Permite que un filósofo libere los tenedores después de comer.
        Esto notifica a otros filósofos que están esperando por los tenedores.

        Args:
            philosopher_id (int): ID del filósofo que quiere liberar los tenedores.
            color (str): Color del filósofo para imprimir mensajes en la consola.
        """
        with self.condition:
            # Liberar ambos tenedores
            left_fork = philosopher_id
            right_fork = (philosopher_id + 1) % self.number_of_philosophers

            self.fork_state[left_fork] = FORK_STATES[0]
            self.fork_state[right_fork] = FORK_STATES[0]
            print(
                f"{color}Filósofo {philosopher_id} suelta tenedores {left_fork} y {right_fork}{RESET}"
            )

            # Notificar a los filósofos en espera
            self.condition.notify_all()


class Philosopher(threading.Thread):
    """Clase que representa a un filósofo en el problema de los filósofos comensales.
    Cada filósofo es un hilo que alterna entre pensar y comer.

    Args:
        threading (Thread): Clase base para crear hilos en Python.
    """

    def __init__(
        self, philosopher_id: int, dining_philosophers: DiningPhilosophers, color: str
    ):
        """Inicializa un filósofo con un ID, un monitor de filósofos comensales y un color para imprimir mensajes.
        Esto permite que cada filósofo actúe de manera independiente y se sincronice con los demás a través del monitor.

        Args:
            philosopher_id (int): ID del filósofo.
            dining_philosophers (DiningPhilosophers): Instancia del monitor de filósofos comensales.
            color (str): Color del filósofo para imprimir mensajes en la consola.
        """
        threading.Thread.__init__(self)
        self.philosopher_id = philosopher_id
        self.dining_philosophers = dining_philosophers
        self.color = color
        self.daemon = True

    def run(self):
        """Ejecutamos de manera indefinida el ciclo de pensar y comer."""
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
    """Función principal para iniciar la simulación de los filósofos comensales.
    Crea una instancia del monitor de filósofos comensales y lanza los hilos de los filósofos.
    Cada filósofo alterna entre pensar y comer, utilizando el monitor para coordinar el acceso a los tenedores.
    """
    dining_philosophers = DiningPhilosophers()

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
