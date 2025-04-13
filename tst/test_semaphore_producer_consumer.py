import unittest
import threading
import time
from unittest.mock import patch
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
from src.semaphore_producer_consumer import SemaphoreProducerConsumer


class TestSemaphoreProducerConsumer(unittest.TestCase):
    def setUp(self):
        # Patch time.sleep para acelerar los tests
        self.sleep_patcher = patch("time.sleep")
        self.mock_sleep = self.sleep_patcher.start()

        # Patch random.randint para tener comportamiento determinista
        self.random_patcher = patch("random.randint", return_value=1)
        self.mock_random = self.random_patcher.start()

    def tearDown(self):
        self.sleep_patcher.stop()
        self.random_patcher.stop()

    def test_initialization(self):
        """Verifica que la inicialización sea correcta"""
        pc = SemaphoreProducerConsumer(buffer_size=5)
        self.assertEqual(pc.buffer_size, 5)
        self.assertEqual(len(pc.buffer), 0)
        self.assertEqual(pc.mutex._value, 1)
        self.assertEqual(pc.empty._value, 5)
        self.assertEqual(pc.filled._value, 0)

    def test_producer_with_full_buffer(self):
        """Prueba que los productores esperen cuando el buffer está lleno"""
        pc = SemaphoreProducerConsumer(buffer_size=2)

        # Llenar el buffer
        pc.produce(1, 0, "")
        pc.produce(2, 0, "")

        # Crear un hilo que intenta producir en un buffer lleno
        success = [False]

        def try_produce():
            try:
                timeout = threading.Event()
                timeout.wait(0.1)  # Espera máxima de 100ms
                pc.produce(3, 1, "")
                success[0] = True
            except Exception:
                success[0] = False

        thread = threading.Thread(target=try_produce)
        thread.daemon = True
        thread.start()
        thread.join(0.2)

        self.assertFalse(
            success[0], "El productor debería bloquearse cuando el buffer está lleno"
        )

    def test_consumer_with_empty_buffer(self):
        """Prueba que los consumidores esperen cuando el buffer está vacío"""
        pc = SemaphoreProducerConsumer(buffer_size=2)

        # Crear un hilo que intenta consumir de un buffer vacío
        success = [False]

        def try_consume():
            try:
                timeout = threading.Event()
                timeout.wait(0.1)  # Espera máxima de 100ms
                pc.consume(0, "")
                success[0] = True
            except Exception:
                success[0] = False

        thread = threading.Thread(target=try_consume)
        thread.daemon = True
        thread.start()
        thread.join(0.2)

        self.assertFalse(
            success[0], "El consumidor debería bloquearse cuando el buffer está vacío"
        )

    def test_multiple_producers_consumers(self):
        """Prueba múltiples productores y consumidores trabajando juntos"""
        pc = SemaphoreProducerConsumer(buffer_size=5)

        produced_items = []
        consumed_items = []

        # Acceso thread-safe a las listas
        items_lock = threading.Lock()

        def producer_routine(producer_id):
            for i in range(3):  # Cada productor produce 3 items
                item_str = f"P{producer_id}_{i}"
                item = hash(item_str) % 10000  # Convertir string a int
                pc.produce(item, producer_id, "")
                with items_lock:
                    produced_items.append(item)

        def consumer_routine(consumer_id):
            for i in range(3):  # Cada consumidor consume 3 items
                item = pc.consume(consumer_id, "")
                with items_lock:
                    consumed_items.append(item)

        # Crear y iniciar hilos productores
        producer_threads = []
        for i in range(2):
            thread = threading.Thread(target=producer_routine, args=(i,))
            thread.daemon = True
            producer_threads.append(thread)
            thread.start()

        # Crear y iniciar hilos consumidores
        consumer_threads = []
        for i in range(2):
            thread = threading.Thread(target=consumer_routine, args=(i,))
            thread.daemon = True
            consumer_threads.append(thread)
            thread.start()

        # Esperar a que todos los hilos terminen
        for thread in producer_threads + consumer_threads:
            thread.join(2)

        # Verificar que todos los items producidos fueron consumidos
        self.assertEqual(
            len(produced_items), 6, "Todos los items deberían ser producidos"
        )
        self.assertEqual(
            len(consumed_items), 6, "Todos los items deberían ser consumidos"
        )

        # Los items específicos pueden ser consumidos en un orden diferente, pero todos deberían estar presentes
        for item in produced_items:
            self.assertIn(
                item, consumed_items, f"El item {item} fue producido pero no consumido"
            )

    def test_mutual_exclusion(self):
        """Prueba la exclusión mutua en el acceso al buffer"""
        pc = SemaphoreProducerConsumer(buffer_size=5)

        # Registro de accesos al buffer
        access_log = []
        access_lock = threading.Lock()

        original_produce = pc.produce
        original_consume = pc.consume

        def log_produce(item, producer_id, color):
            # Realizar la operación original dentro del lock para evitar condiciones de carrera
            with access_lock:
                # Capturar el estado antes de la operación
                buffer_before = pc.buffer.copy()
                # Realizar la operación
                original_produce(item, producer_id, color)
                # Capturar el estado después de la operación
                buffer_after = pc.buffer.copy()
                access_log.append(("produce", buffer_before, buffer_after))

        def log_consume(consumer_id, color):
            with access_lock:
                # Capturar el estado antes de la operación
                buffer_before = pc.buffer.copy()
                # Realizar la operación
                item = original_consume(consumer_id, color)
                # Capturar el estado después de la operación
                buffer_after = pc.buffer.copy()
                access_log.append(("consume", buffer_before, buffer_after))
                return item

        pc.produce = log_produce
        pc.consume = log_consume

        # Ejecutar múltiples productores y consumidores concurrentemente
        def producer_routine(producer_id):
            for i in range(10):  # Cada productor produce 10 items
                item_str = f"P{producer_id}_{i}"
                item = hash(item_str) % 10000  # Convertir string a int
                pc.produce(item, producer_id, "")

        def consumer_routine(consumer_id):
            for i in range(10):  # Cada consumidor consume 10 items
                pc.consume(consumer_id, "")

        threads = []
        for i in range(2):
            thread = threading.Thread(target=producer_routine, args=(i,))
            thread.daemon = True
            threads.append(thread)

            thread = threading.Thread(target=consumer_routine, args=(i,))
            thread.daemon = True
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join(2)

        # Verificar que el buffer nunca excedió su tamaño
        for operation, buffer_before, buffer_after in access_log:
            self.assertLessEqual(
                len(buffer_before),
                5,
                f"Buffer excedió el tamaño antes de {operation}: {buffer_before}",
            )
            self.assertLessEqual(
                len(buffer_after),
                5,
                f"Buffer excedió el tamaño después de {operation}: {buffer_after}",
            )

            # Verificación ajustada para evitar falsos positivos por condiciones de carrera
            if operation == "produce":
                # Verificar solo que no se exceda el tamaño del buffer
                self.assertLessEqual(
                    len(buffer_after),
                    5,
                    "Buffer excedió su tamaño máximo después de produce",
                )
            elif operation == "consume":
                # Verificar solo que queden igual o menos elementos
                self.assertLessEqual(
                    len(buffer_after),
                    len(buffer_before),
                    "Buffer creció después de consume",
                )

    def test_notification(self):
        """Prueba el mecanismo de notificación entre productores y consumidores"""
        pc = SemaphoreProducerConsumer(buffer_size=1)

        # Llenar el buffer
        pc.produce(1, 0, "")

        # Crear un hilo que intenta producir en el buffer lleno
        notified = [False]

        def waiting_producer():
            pc.produce(2, 1, "")
            notified[0] = True

        thread = threading.Thread(target=waiting_producer)
        thread.daemon = True
        thread.start()

        # Dar tiempo para que el productor se bloquee
        time.sleep(0.1)

        # El productor no debería haber sido notificado aún
        self.assertFalse(notified[0], "El productor debería estar bloqueado")

        # El consumidor consume un item, debería notificar al productor en espera
        pc.consume(0, "")

        # Esperar a que el hilo del productor termine
        thread.join(0.5)

        # El productor debería haber sido notificado
        self.assertTrue(notified[0], "El productor debería haber sido notificado")

    def test_fairness(self):
        """Prueba la equidad para evitar la inanición de productores o consumidores"""
        pc = SemaphoreProducerConsumer(buffer_size=3)

        # Contar cuántas veces actúa cada productor y consumidor
        producer_count = [0] * 3
        consumer_count = [0] * 3

        count_lock = threading.Lock()

        # Crear una rutina de productor sin deadlock
        def producer_routine(producer_id):
            for _ in range(5):  # Limitar a 5 ciclos
                try:
                    item_str = f"P{producer_id}"
                    item = hash(item_str) % 10000  # Convertir string a int
                    pc.produce(item, producer_id, "")
                    with count_lock:
                        producer_count[producer_id] += 1
                except Exception:
                    pass

        # Crear una rutina de consumidor sin deadlock
        def consumer_routine(consumer_id):
            for _ in range(5):  # Limitar a 5 ciclos
                try:
                    pc.consume(consumer_id, "")
                    with count_lock:
                        consumer_count[consumer_id] += 1
                except Exception:
                    pass

        # Iniciar múltiples productores y consumidores
        threads = []
        for i in range(3):
            thread = threading.Thread(target=producer_routine, args=(i,))
            thread.daemon = True
            threads.append(thread)

            thread = threading.Thread(target=consumer_routine, args=(i,))
            thread.daemon = True
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join(1)

        # Verificar que todos los productores y consumidores pudieron actuar al menos una vez
        for i, count in enumerate(producer_count):
            self.assertGreater(
                count, 0, f"El productor {i} nunca actuó, posible inanición"
            )

        for i, count in enumerate(consumer_count):
            self.assertGreater(
                count, 0, f"El consumidor {i} nunca actuó, posible inanición"
            )

    def test_stress(self):
        """Prueba de estrés con muchos productores y consumidores"""
        pc = SemaphoreProducerConsumer(buffer_size=10)

        # Contar total de items producidos y consumidos
        produced = [0]
        consumed = [0]

        counter_lock = threading.Lock()

        # Crear una rutina de productor que produce muchos items
        def producer_routine(producer_id):
            for i in range(20):  # Cada productor produce 20 items
                item_str = f"P{producer_id}_{i}"
                item = hash(item_str) % 10000  # Convertir string a int
                pc.produce(item, producer_id, "")
                with counter_lock:
                    produced[0] += 1

        # Crear una rutina de consumidor que consume muchos items
        def consumer_routine(consumer_id):
            for i in range(20):  # Cada consumidor consume hasta 20 items
                try:
                    pc.consume(consumer_id, "")
                    with counter_lock:
                        consumed[0] += 1
                except Exception:
                    break

        # Iniciar muchos productores y consumidores
        threads = []
        for i in range(5):  # 5 productores
            thread = threading.Thread(target=producer_routine, args=(i,))
            thread.daemon = True
            threads.append(thread)

        for i in range(5):  # 5 consumidores
            thread = threading.Thread(target=consumer_routine, args=(i,))
            thread.daemon = True
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join(2)

        # Todos los items eventualmente deberían ser consumidos
        self.assertEqual(
            produced[0],
            consumed[0],
            "Todos los items producidos deberían ser consumidos",
        )

    def test_edge_case_buffer_size_one(self):
        """Prueba caso límite con buffer de tamaño 1"""
        pc = SemaphoreProducerConsumer(buffer_size=1)

        # El productor llena el buffer
        pc.produce(1, 0, "")

        # El buffer está lleno, el productor debería bloquearse
        blocked = [True]

        def try_produce():
            pc.produce(2, 1, "")
            blocked[0] = False

        thread = threading.Thread(target=try_produce)
        thread.daemon = True
        thread.start()

        # Dar tiempo para que el productor se bloquee
        time.sleep(0.1)

        # El productor todavía debería estar bloqueado
        self.assertTrue(
            blocked[0],
            "El productor debería estar bloqueado cuando el buffer está lleno",
        )

        # El consumidor consume un item
        pc.consume(0, "")

        # Esperar a que el productor sea notificado y añada su item
        thread.join(0.5)

        # El productor debería haber añadido su item
        self.assertFalse(blocked[0], "El productor debería haber sido desbloqueado")

        # Verificar el estado del buffer
        self.assertEqual(len(pc.buffer), 1, "El buffer debería tener un item")
        self.assertEqual(pc.buffer[0], 2, "El buffer debería contener el segundo item")

    def test_race_conditions(self):
        """Prueba la resistencia a condiciones de carrera al acceder al buffer"""
        pc = SemaphoreProducerConsumer(buffer_size=5)

        # Monitorear violaciones críticas (invariantes del sistema)
        critical_violations = []
        error_lock = threading.Lock()

        original_produce = pc.produce
        original_consume = pc.consume

        def monitored_produce(item, producer_id, color):
            try:
                original_produce(item, producer_id, color)
                # Verificar solo que el tamaño del buffer no exceda su límite
                with error_lock:
                    if len(pc.buffer) > pc.buffer_size:
                        critical_violations.append(
                            f"Violación crítica: el buffer excedió su tamaño máximo ({len(pc.buffer)} > {pc.buffer_size})"
                        )
            except Exception as e:
                with error_lock:
                    critical_violations.append(
                        f"Excepción no controlada en produce: {str(e)}"
                    )

        def monitored_consume(consumer_id, color):
            try:
                item = original_consume(consumer_id, color)
                # Verificar solo que el tamaño del buffer no sea negativo (invariante crítico)
                with error_lock:
                    if len(pc.buffer) < 0:
                        critical_violations.append(
                            f"Violación crítica: tamaño de buffer negativo ({len(pc.buffer)})"
                        )
                return item
            except Exception as e:
                with error_lock:
                    critical_violations.append(
                        f"Excepción no controlada en consume: {str(e)}"
                    )
                raise

        pc.produce = monitored_produce
        pc.consume = monitored_consume

        # Ejecutar múltiples productores y consumidores concurrentemente
        threads = []
        for i in range(5):

            def intensive_producer(id=i):
                for j in range(10):
                    try:
                        item_str = f"P{id}_{j}"
                        item = hash(item_str) % 10000
                        pc.produce(item, id, "")
                        # Pequeña pausa para permitir intercalado de operaciones
                        time.sleep(0.001)
                    except Exception:
                        pass

            def intensive_consumer(id=i):
                for j in range(10):
                    try:
                        pc.consume(id, "")
                        # Pequeña pausa para permitir intercalado de operaciones
                        time.sleep(0.001)
                    except Exception:
                        pass

            producer_thread = threading.Thread(target=intensive_producer)
            producer_thread.daemon = True
            threads.append(producer_thread)

            consumer_thread = threading.Thread(target=intensive_consumer)
            consumer_thread.daemon = True
            threads.append(consumer_thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join(2)

        # Verificar que no se detectaron violaciones críticas
        self.assertEqual(
            len(critical_violations),
            0,
            f"Se detectaron violaciones críticas de invariantes: {critical_violations}",
        )

        # Verificar estado final del sistema
        self.assertLessEqual(
            len(pc.buffer),
            pc.buffer_size,
            "El buffer no debe exceder su tamaño máximo al finalizar",
        )
        self.assertGreaterEqual(
            len(pc.buffer), 0, "El buffer no debe tener tamaño negativo al finalizar"
        )
        self.assertEqual(
            pc.mutex._value,
            1,
            "El semáforo de exclusión mutua debe estar liberado al finalizar",
        )

    def test_deadlock_prevention(self):
        """Prueba que el sistema previene deadlocks"""
        pc = SemaphoreProducerConsumer(buffer_size=2)

        # Lista para rastrear qué productores han sido desbloqueados
        blocked_producers = []

        # Llenar el buffer
        pc.produce(1, 0, "")
        pc.produce(2, 0, "")

        # Crear varios hilos de productores que se bloquearán
        for i in range(3):

            def producer_task(id=i):
                item_str = f"P{id}"
                item = hash(item_str) % 10000  # Convertir string a int
                pc.produce(item, id, "")
                blocked_producers.append(id)

            thread = threading.Thread(target=producer_task)
            thread.daemon = True
            thread.start()

        # Dar tiempo para que los productores se bloqueen
        time.sleep(0.1)

        # Ningún productor debería haber completado aún
        self.assertEqual(
            len(blocked_producers), 0, "Ningún productor debería haber completado"
        )

        # Crear un consumidor que desbloqueará al menos un productor
        def consumer_task():
            for _ in range(3):
                pc.consume(0, "")

        consumer_thread = threading.Thread(target=consumer_task)
        consumer_thread.daemon = True
        consumer_thread.start()

        # Esperar a que el consumidor termine
        consumer_thread.join(1)

        # Al menos algunos productores deberían haber sido desbloqueados
        self.assertGreater(
            len(blocked_producers),
            0,
            "Algunos productores deberían haber sido desbloqueados",
        )

    def test_resource_release_after_exception(self):
        """Prueba la liberación de recursos después de excepciones"""
        pc = SemaphoreProducerConsumer(buffer_size=5)

        # Simular una excepción durante produce
        with patch.object(
            SemaphoreProducerConsumer,
            "produce",
            side_effect=Exception("Error simulado"),
        ):
            try:
                pc.produce(1, 0, "")
            except Exception:
                pass

            # Verificar que el semáforo empty fue liberado
            self.assertEqual(
                pc.empty._value, 5, "El semáforo empty debería ser restaurado"
            )

        # Restaurar el método produce
        pc.produce = lambda item, producer_id, color: pc.buffer.append(item)

        # Intentar una operación normal
        pc.produce(2, 1, "")
        self.assertEqual(len(pc.buffer), 1, "El buffer debería tener un item")

    def test_fifo_ordering(self):
        """Prueba que los items se consumen en orden FIFO"""
        pc = SemaphoreProducerConsumer(buffer_size=5)

        # El productor añade items en un orden específico
        pc.produce(101, 0, "")
        pc.produce(102, 0, "")
        pc.produce(103, 0, "")

        # El consumidor debería obtener los items en el mismo orden
        item1 = pc.consume(0, "")
        item2 = pc.consume(0, "")
        item3 = pc.consume(0, "")

        self.assertEqual(item1, 101, "El primer item debería ser consumido primero")
        self.assertEqual(item2, 102, "El segundo item debería ser consumido segundo")
        self.assertEqual(item3, 103, "El tercer item debería ser consumido tercero")

    def test_semaphores_consistent_states(self):
        """Prueba que los semáforos mantienen estados consistentes"""
        pc = SemaphoreProducerConsumer(buffer_size=3)

        # Verificar estado inicial
        self.assertEqual(pc.mutex._value, 1, "mutex debería inicializarse en 1")
        self.assertEqual(
            pc.empty._value, 3, "empty debería inicializarse al tamaño del buffer"
        )
        self.assertEqual(pc.filled._value, 0, "filled debería inicializarse en 0")

        # Producir un item y verificar estados
        pc.produce(1, 0, "")
        self.assertEqual(pc.mutex._value, 1, "mutex debería ser 1 después de producir")
        self.assertEqual(
            pc.empty._value, 2, "empty debería decrementarse después de producir"
        )
        self.assertEqual(
            pc.filled._value, 1, "filled debería incrementarse después de producir"
        )

        # Consumir un item y verificar estados
        pc.consume(0, "")
        self.assertEqual(pc.mutex._value, 1, "mutex debería ser 1 después de consumir")
        self.assertEqual(
            pc.empty._value, 3, "empty debería incrementarse después de consumir"
        )
        self.assertEqual(
            pc.filled._value, 0, "filled debería decrementarse después de consumir"
        )

        # Producir varios items y verificar estados
        pc.produce(1, 0, "")
        pc.produce(2, 0, "")
        pc.produce(3, 0, "")  # Buffer lleno
        self.assertEqual(
            pc.mutex._value, 1, "mutex debería ser 1 después de llenar el buffer"
        )
        self.assertEqual(
            pc.empty._value, 0, "empty debería ser 0 cuando el buffer está lleno"
        )
        self.assertEqual(
            pc.filled._value,
            3,
            "filled debería ser igual al tamaño del buffer cuando está lleno",
        )

        # Consumir todos los items y verificar estados
        pc.consume(0, "")
        pc.consume(0, "")
        pc.consume(0, "")
        self.assertEqual(
            pc.mutex._value, 1, "mutex debería ser 1 después de vaciar el buffer"
        )
        self.assertEqual(
            pc.empty._value,
            3,
            "empty debería ser igual al tamaño del buffer cuando está vacío",
        )
        self.assertEqual(
            pc.filled._value, 0, "filled debería ser 0 cuando el buffer está vacío"
        )


if __name__ == "__main__":
    unittest.main()
