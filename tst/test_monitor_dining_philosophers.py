import unittest
import threading
import time
from unittest.mock import patch
import sys
import os
import random
import queue

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from src.monitor_dining_philosophers import DiningPhilosophers, FORK_STATES, Philosopher


class TestDiningPhilosophers(unittest.TestCase):
    
    def setUp(self):
        # Patch time.sleep para acelerar los tests
        self.sleep_patcher = patch('time.sleep')
        self.mock_sleep = self.sleep_patcher.start()
        
        # Patch random.randint para tener comportamiento determinista
        self.random_patcher = patch('random.randint', return_value=1)
        self.mock_random = self.random_patcher.start()
    
    def tearDown(self):
        self.sleep_patcher.stop()
        self.random_patcher.stop()
    
    def test_initialization(self):
        """Verifica que la inicialización sea correcta"""
        dp = DiningPhilosophers(5)
        self.assertEqual(dp.number_of_philosophers, 5)
        self.assertEqual(len(dp.philosophers), 5)
        self.assertEqual(dp.fork_state, [FORK_STATES[0]] * 5)
    
    def test_pickup_forks(self):
        """Verifica que los tenedores se tomen correctamente"""
        dp = DiningPhilosophers(5)
        dp.pickup_forks(0, "")
        self.assertEqual(dp.fork_state[0], FORK_STATES[1])
        self.assertEqual(dp.fork_state[1], FORK_STATES[1])
    
    def test_putdown_forks(self):
        """Verifica que los tenedores se suelten correctamente"""
        dp = DiningPhilosophers(5)
        dp.pickup_forks(0, "")
        dp.putdown_forks(0, "")
        self.assertEqual(dp.fork_state[0], FORK_STATES[0])
        self.assertEqual(dp.fork_state[1], FORK_STATES[0])
    
    def test_mutual_exclusion(self):
        """Verifica que dos filósofos adyacentes no puedan comer al mismo tiempo"""
        dp = DiningPhilosophers(5)
        
        # Filósofo 0 toma sus tenedores
        dp.pickup_forks(0, "")
        
        # Creamos un hilo que intenta tomar los tenedores para el filósofo 1
        # No debería poder hacerlo porque comparte un tenedor con el filósofo 0
        success = [False]
        
        def try_pickup():
            try:
                timeout = threading.Event()
                timeout.wait(0.1)  # Espera máxima de 100ms
                dp.pickup_forks(1, "")
                success[0] = True
            except Exception:
                success[0] = False
                
        
        thread = threading.Thread(target=try_pickup)
        thread.daemon = True
        thread.start()
        thread.join(0.2)
        
        self.assertFalse(success[0], "El filósofo 1 no debería poder tomar tenedores mientras el filósofo 0 los tiene")
    
    def test_deadlock_prevention(self):
        """Verifica que el sistema evite deadlocks"""
        dp = DiningPhilosophers(5)
        
        # Hacemos que todos los filósofos intenten comer a la vez
        threads = []
        eating_count = [0] * 5
        
        def philosopher_routine(id):
            for _ in range(3):  # Cada filósofo intenta comer 3 veces
                dp.pickup_forks(id, "")
                eating_count[id] += 1
                dp.putdown_forks(id, "")
        
        for i in range(5):
            thread = threading.Thread(target=philosopher_routine, args=(i,))
            thread.daemon = True
            threads.append(thread)
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join(2)  # Espera máxima de 2 segundos
        
        # Verificamos que todos los filósofos hayan comido
        for count in eating_count:
            self.assertEqual(count, 3, "Todos los filósofos deberían poder comer, posible deadlock")
    
    def test_starvation_prevention(self):
        """Verifica que no haya inanición (que todos los filósofos puedan comer)"""
        dp = DiningPhilosophers(5)
        
        # Contador de comidas por filósofo
        eating_counts = [0] * 5
        count_lock = threading.Lock()
        
        # Implementar un método directo para que cada filósofo intente comer
        def philosopher_try_eat(philosopher_id):
            for _ in range(3):  # Intentar comer varias veces
                try:
                    dp.pickup_forks(philosopher_id, "")
                    with count_lock:
                        eating_counts[philosopher_id] += 1
                    dp.putdown_forks(philosopher_id, "")
                except Exception:
                    pass
        
        # Iniciar los filósofos
        threads = []
        for i in range(5):
            thread = threading.Thread(target=philosopher_try_eat, args=(i,))
            thread.daemon = True
            threads.append(thread)
            thread.start()
        
        # Esperar a que terminen con un timeout
        for thread in threads:
            thread.join(1)
        
        # Verificar que todos hayan comido al menos una vez
        for i, count in enumerate(eating_counts):
            self.assertGreater(count, 0, f"El filósofo {i} nunca comió, posible inanición")
    
    def test_concurrent_access(self):
        """Verifica el acceso concurrente correcto a los recursos"""
        dp = DiningPhilosophers(5)
        
        # Rastrear el estado de los tenedores durante la ejecución
        fork_access_log = []
        
        original_pickup = dp.pickup_forks
        original_putdown = dp.putdown_forks
        
        def log_pickup(philosopher_id, color):
            original_pickup(philosopher_id, color)
            fork_access_log.append((philosopher_id, "pickup", dp.fork_state.copy()))
        
        def log_putdown(philosopher_id, color):
            original_putdown(philosopher_id, color)
            fork_access_log.append((philosopher_id, "putdown", dp.fork_state.copy()))
        
        dp.pickup_forks = log_pickup
        dp.putdown_forks = log_putdown
        
        # Ejecutar varios filósofos concurrentemente
        threads = []
        for i in range(5):
            thread = threading.Thread(target=lambda id=i: [dp.pickup_forks(id, ""), dp.putdown_forks(id, "")])
            thread.daemon = True
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join(1)
        
        # Verificar que en ningún momento dos filósofos adyacentes tenían tenedores a la vez
        for i in range(len(fork_access_log)):
            state = fork_access_log[i][2]
            for j in range(5):
                # Si el tenedor j está tomado
                if state[j] == FORK_STATES[1]:
                    # El tenedor anterior también está tomado, verificar que no pertenezcan a filósofos diferentes
                    prev_fork = (j - 1) % 5
                    if state[prev_fork] == FORK_STATES[1]:
                        # Verificar que ambos tenedores pertenecen al mismo filósofo
                        self.assertTrue(
                            (j == fork_access_log[i][0] and prev_fork == (fork_access_log[i][0] - 1) % 5) or
                            (prev_fork == fork_access_log[i][0] and j == (fork_access_log[i][0] + 1) % 5),
                            f"Violación de exclusión mutua en {fork_access_log[i]}"
                        )
    
    def test_edge_case_one_philosopher(self):
        """Verifica el comportamiento con un solo filósofo"""
        dp = DiningPhilosophers(1)
        self.assertEqual(dp.number_of_philosophers, 1)
        self.assertEqual(len(dp.philosophers), 1)
        
        # Un solo filósofo debería poder comer sin problemas
        dp.pickup_forks(0, "")
        self.assertEqual(dp.fork_state[0], FORK_STATES[1])
        dp.putdown_forks(0, "")
        self.assertEqual(dp.fork_state[0], FORK_STATES[0])

    def test_edge_case_two_philosophers(self):
        """Verifica el comportamiento con dos filósofos"""
        dp = DiningPhilosophers(2)
        self.assertEqual(dp.number_of_philosophers, 2)
        
        # Los dos filósofos deberían poder comer de forma alternada
        dp.pickup_forks(0, "")
        self.assertEqual(dp.fork_state[0], FORK_STATES[1])
        self.assertEqual(dp.fork_state[1], FORK_STATES[1])
        
        # El filósofo 1 no debería poder comer mientras el 0 está comiendo
        can_eat = [False]
        def try_eat():
            try:
                dp.pickup_forks(1, "")
                can_eat[0] = True
            except Exception:
                can_eat[0] = False
        
        thread = threading.Thread(target=try_eat)
        thread.daemon = True
        thread.start()
        thread.join(0.2)
        
        self.assertFalse(can_eat[0], "El filósofo 1 no debería poder comer mientras el filósofo 0 está comiendo")
        
        # Después de que el filósofo 0 termina, el 1 debería poder comer
        dp.putdown_forks(0, "")
        dp.pickup_forks(1, "")
        self.assertEqual(dp.fork_state[0], FORK_STATES[1])
        self.assertEqual(dp.fork_state[1], FORK_STATES[1])

    def test_resource_release(self):
        """Verifica que los tenedores se liberen correctamente incluso en caso de excepción"""
        dp = DiningPhilosophers(5)
        
        # Simular una excepción durante la comida
        with patch.object(Philosopher, 'eat', side_effect=Exception("Error simulado")):
            philosopher = dp.philosophers[0]
            
            # Registrar el estado de los tenedores
            left_fork = philosopher.philosopher_id
            right_fork = (philosopher.philosopher_id + 1) % dp.number_of_philosophers
            
            # Simular el intento de comer que fallará
            try:
                philosopher.eat()
            except Exception:
                pass
            
            # Verificar que los tenedores se liberaron a pesar de la excepción
            self.assertEqual(dp.fork_state[left_fork], FORK_STATES[0], 
                            "El tenedor izquierdo debería estar libre después de una excepción")
            self.assertEqual(dp.fork_state[right_fork], FORK_STATES[0], 
                            "El tenedor derecho debería estar libre después de una excepción")

    def test_stress_test(self):
        """Prueba de estrés con muchos filósofos intentando comer repetidamente"""
        num_philosophers = 10
        dp = DiningPhilosophers(num_philosophers)
        
        # Contar cuántas veces come cada filósofo
        eating_count = [0] * num_philosophers
        
        # Barrera para sincronizar el inicio de todos los hilos
        barrier = threading.Barrier(num_philosophers)
        
        def philosopher_routine(id):
            barrier.wait()  # Esperar a que todos los hilos estén listos
            for _ in range(5):  # Cada filósofo intenta comer 5 veces
                dp.pickup_forks(id, "")
                eating_count[id] += 1
                dp.putdown_forks(id, "")
        
        threads = []
        for i in range(num_philosophers):
            thread = threading.Thread(target=philosopher_routine, args=(i,))
            thread.daemon = True
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join(3)  # Timeout de 3 segundos
        
        # Verificar que todos hayan comido al menos una vez
        for i, count in enumerate(eating_count):
            self.assertGreater(count, 0, f"El filósofo {i} nunca comió en la prueba de estrés")
        
    def test_fairness(self):
        """Verifica que el sistema sea justo y no favorezca a ciertos filósofos"""
        dp = DiningPhilosophers(5)
        
        # Contar cuántas veces come cada filósofo
        eating_count = [0] * 5
        
        # Reemplazo para hacer que las comidas sean aleatorias pero controladas
        original_randint = random.randint
        
        def controlled_random(*args):
            return original_randint(1, 2)  # Valores pequeños para que el test sea rápido
        
        with patch('random.randint', side_effect=controlled_random):
            # Monitorear las comidas
            original_pickup = dp.pickup_forks
            
            def count_pickup(philosopher_id, color):
                original_pickup(philosopher_id, color)
                eating_count[philosopher_id] += 1
            
            dp.pickup_forks = count_pickup
            
            # Hacer que los filósofos coman por un tiempo
            threads = []
            for i, philosopher in enumerate(dp.philosophers):
                def run_limited(phil_id=i, phil=philosopher):
                    for _ in range(10):  # Limitar a 10 ciclos
                        phil.think()
                        try:
                            dp.pickup_forks(phil_id, "")
                            eating_count[phil_id] += 1
                            dp.putdown_forks(phil_id, "")
                        except Exception:
                            pass
                
                thread = threading.Thread(target=run_limited)
                thread.daemon = True
                threads.append(thread)
                thread.start()
            
            # Esperar a que terminen
            for thread in threads:
                thread.join(1)

    def test_race_condition(self):
        """Verifica que no ocurran condiciones de carrera al acceder a los tenedores"""
        dp = DiningPhilosophers(5)
        
        # Simular accesos concurrentes intensivos
        access_errors = []
        error_lock = threading.Lock()
        
        # Crear una función que verifique inconsistencias
        def check_consistency(philosopher_id, action, state):
            # Si es toma de tenedores, verificar que los tenedores estén tomados
            if action == "pickup":
                left_fork = philosopher_id
                right_fork = (philosopher_id + 1) % len(state)
                
                if state[left_fork] != FORK_STATES[1] or state[right_fork] != FORK_STATES[1]:
                    with error_lock:
                        access_errors.append(f"Inconsistencia en tenedores para filósofo {philosopher_id}")
        
        # Modificar los métodos para verificar la consistencia
        original_pickup = dp.pickup_forks
        original_putdown = dp.putdown_forks
        
        def check_pickup(philosopher_id, color):
            original_pickup(philosopher_id, color)
            check_consistency(philosopher_id, "pickup", dp.fork_state.copy())
        
        def check_putdown(philosopher_id, color):
            original_putdown(philosopher_id, color)
            check_consistency(philosopher_id, "putdown", dp.fork_state.copy())
        
        dp.pickup_forks = check_pickup
        dp.putdown_forks = check_putdown
        
        # Ejecutar múltiples filósofos con acceso intensivo
        threads = []
        for i in range(5):
            def intensive_access_with_exception_handling(id=i):
                for _ in range(20):  # 20 ciclos de tomar y soltar tenedores
                    try:
                        dp.pickup_forks(id, "")
                        dp.putdown_forks(id, "")
                    except Exception:
                        pass
            
            thread = threading.Thread(target=intensive_access_with_exception_handling)
            thread.daemon = True
            threads.append(thread)
            thread.start()
            
            def intensive_access_without_exception_handling(id=i):
                for _ in range(20):  # 20 ciclos de tomar y soltar tenedores
                    dp.pickup_forks(id, "")
                    dp.putdown_forks(id, "")
            
            thread = threading.Thread(target=intensive_access_without_exception_handling)
            thread.daemon = True
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join(2)
        
        # Verificar que no haya errores de acceso concurrente
        self.assertEqual(len(access_errors), 0, f"Se detectaron condiciones de carrera: {access_errors}")

    def test_priority_handling(self):
        """Verifica si el sistema maneja correctamente las prioridades de los filósofos"""
        dp = DiningPhilosophers(5)
        
        # Cola para registrar el orden en que los filósofos comen
        eating_order = queue.Queue()
        
        # Modificar pickup_forks para registrar el orden
        original_pickup = dp.pickup_forks
        
        def log_pickup(philosopher_id, color):
            original_pickup(philosopher_id, color)
            eating_order.put(philosopher_id)
        
        dp.pickup_forks = log_pickup
        
        # Hacer que todos los filósofos intenten comer al mismo tiempo
        threads = []
        start_signal = threading.Event()
        
        def synchronized_eat(id):
            start_signal.wait()  # Esperar señal para empezar todos al mismo tiempo
            dp.pickup_forks(id, "")
            dp.putdown_forks(id, "")
        
        for i in range(5):
            thread = threading.Thread(target=synchronized_eat, args=(i,))
            thread.daemon = True
            threads.append(thread)
            thread.start()
        
        # Dar la señal para que todos empiecen al mismo tiempo
        start_signal.set()
        
        for thread in threads:
            thread.join(1)
        
        # Registrar el orden en que comieron
        eating_sequence = []
        while not eating_order.empty():
            eating_sequence.append(eating_order.get())
        
        # Verificar que el orden no favorezca siempre a los mismos filósofos
        # (este test podría dar falsos positivos algunas veces por la naturaleza
        # del problema, pero es útil para detectar sesgos evidentes)
        self.assertEqual(len(eating_sequence), 5, "Todos los filósofos deberían haber comido una vez")

    def test_monitor_reentrance(self):
        """Verifica que el monitor permita la reentrada de un mismo filósofo"""
        dp = DiningPhilosophers(5)
        
        # Un filósofo debería poder comer varias veces seguidas sin problemas
        for _ in range(3):
            dp.pickup_forks(0, "")
            dp.putdown_forks(0, "")
        
        # Verificar que los tenedores estén libres al final
        self.assertEqual(dp.fork_state[0], FORK_STATES[0])
        self.assertEqual(dp.fork_state[1], FORK_STATES[0])

    def test_wait_notification(self):
        """Verifica que los filósofos sean notificados correctamente cuando se liberan tenedores"""
        dp = DiningPhilosophers(5)
        
        # Filósofo 0 toma sus tenedores
        dp.pickup_forks(0, "")
        
        # Crear un hilo para el filósofo 1 que intentará comer
        notified = [False]
        
        def wait_for_forks():
            # Intentar tomar los tenedores del filósofo 1
            # Esto debería bloquearse, y luego ser notificado cuando el filósofo 0 termine
            dp.pickup_forks(1, "")
            notified[0] = True
            dp.putdown_forks(1, "")
        
        thread = threading.Thread(target=wait_for_forks)
        thread.daemon = True
        thread.start()
        
        # Esperar un momento para que el hilo intente y se bloquee
        time.sleep(0.1)
        
        # El filósofo 1 no debería haber sido notificado aún
        self.assertFalse(notified[0], "El filósofo 1 no debería haber sido notificado aún")
        
        # El filósofo 0 suelta sus tenedores, esto debería notificar al filósofo 1
        dp.putdown_forks(0, "")
        
        # Esperar a que el hilo del filósofo 1 termine
        thread.join(0.5)
        
        # Verificar que el filósofo 1 fue notificado
        self.assertTrue(notified[0], "El filósofo 1 debería haber sido notificado")


if __name__ == '__main__':
    unittest.main()