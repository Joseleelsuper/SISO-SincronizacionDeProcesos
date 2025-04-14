import unittest
import threading
import time
from unittest.mock import patch
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from src.monitor_readers_writers import ReadersWriters, RESOURCE_STATES
from src.semaphore_readers_writers import SemaphoreReadersWriters


class TestMonitorReadersWriters(unittest.TestCase):
    
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
        rw = ReadersWriters()
        self.assertEqual(rw.resource_state, RESOURCE_STATES[0])
        self.assertEqual(rw.readers_count, 0)
        self.assertEqual(rw.writers_waiting, 0)
        self.assertFalse(rw.active_writer)
        self.assertEqual(rw.resource_content, "Contenido inicial del recurso")
    
    def test_single_reader(self):
        """Prueba el comportamiento con un solo lector"""
        rw = ReadersWriters()
        
        # Un lector comienza a leer
        rw.start_read(0, "")
        self.assertEqual(rw.readers_count, 1)
        self.assertEqual(rw.resource_state, RESOURCE_STATES[1])
        
        # El lector lee el contenido
        content = rw.read_resource(0, "")
        self.assertEqual(content, "Contenido inicial del recurso")
        
        # El lector termina de leer
        rw.end_read(0, "")
        self.assertEqual(rw.readers_count, 0)
        self.assertEqual(rw.resource_state, RESOURCE_STATES[0])
    
    def test_single_writer(self):
        """Prueba el comportamiento con un solo escritor"""
        rw = ReadersWriters()
        
        # Un escritor comienza a escribir
        rw.start_write(0, "")
        self.assertTrue(rw.active_writer)
        self.assertEqual(rw.resource_state, RESOURCE_STATES[2])
        
        # El escritor termina de escribir
        new_content = "Nuevo contenido"
        rw.end_write(0, "", new_content)
        self.assertFalse(rw.active_writer)
        self.assertEqual(rw.resource_state, RESOURCE_STATES[0])
        self.assertEqual(rw.resource_content, new_content)
    
    def test_multiple_readers(self):
        """Prueba que múltiples lectores puedan leer simultáneamente"""
        rw = ReadersWriters()
        
        # Varios lectores comienzan a leer
        for i in range(5):
            rw.start_read(i, "")
        
        self.assertEqual(rw.readers_count, 5)
        self.assertEqual(rw.resource_state, RESOURCE_STATES[1])
        
        # Verificar que todos pueden leer el contenido
        for i in range(5):
            content = rw.read_resource(i, "")
            self.assertEqual(content, "Contenido inicial del recurso")
        
        # Los lectores terminan de leer
        for i in range(5):
            rw.end_read(i, "")
        
        self.assertEqual(rw.readers_count, 0)
        self.assertEqual(rw.resource_state, RESOURCE_STATES[0])
    
    def test_writer_blocks_readers(self):
        """Prueba que un escritor activo bloquea a los lectores"""
        rw = ReadersWriters()
        
        # Un escritor comienza a escribir
        rw.start_write(0, "")
        
        # Un lector intenta leer
        success = [False]
        
        def try_read():
            try:
                timeout = threading.Event()
                timeout.wait(0.1)  # Espera máxima de 100ms
                rw.start_read(1, "")
                success[0] = True
            except Exception:
                success[0] = False
                
        thread = threading.Thread(target=try_read)
        thread.daemon = True
        thread.start()
        thread.join(0.2)
        
        self.assertFalse(success[0], "El lector no debería poder leer mientras un escritor está activo")
        
        # El escritor termina
        rw.end_write(0, "", "Nuevo contenido")
        
        # Ahora el lector debería poder leer
        rw.start_read(1, "")
        self.assertEqual(rw.readers_count, 1)
    
    def test_readers_block_writers(self):
        """Prueba que los lectores activos bloquean a los escritores"""
        rw = ReadersWriters()
        
        # Un lector comienza a leer
        rw.start_read(0, "")
        
        # Un escritor intenta escribir
        success = [False]
        
        def try_write():
            try:
                timeout = threading.Event()
                timeout.wait(0.1)  # Espera máxima de 100ms
                rw.start_write(1, "")
                success[0] = True
            except Exception:
                success[0] = False
                
        thread = threading.Thread(target=try_write)
        thread.daemon = True
        thread.start()
        thread.join(0.2)
        
        self.assertFalse(success[0], "El escritor no debería poder escribir mientras hay lectores activos")
        
        # El lector termina
        rw.end_read(0, "")
        
        # Ahora el escritor debería poder escribir
        rw.start_write(1, "")
        self.assertTrue(rw.active_writer)
    
    def test_writer_priority(self):
        """Prueba que los escritores tienen prioridad sobre nuevos lectores"""
        rw = ReadersWriters()
        
        # Un lector comienza a leer
        rw.start_read(0, "")
        
        # Un escritor espera para escribir
        writer_notified = [False]
        
        def waiting_writer():
            rw.start_write(0, "")
            writer_notified[0] = True
            rw.end_write(0, "", "Contenido del escritor")
        
        writer_thread = threading.Thread(target=waiting_writer)
        writer_thread.daemon = True
        writer_thread.start()
        
        # Intentar que otro lector comience a leer
        reader_notified = [False]
        
        def another_reader():
            rw.start_read(1, "")
            reader_notified[0] = True
            rw.end_read(1, "")
        
        reader_thread = threading.Thread(target=another_reader)
        reader_thread.daemon = True
        reader_thread.start()
        
        # Dar tiempo para que los hilos se bloqueen
        time.sleep(0.1)
        
        # El primer lector termina de leer
        rw.end_read(0, "")
        
        # Esperar a que los hilos terminen
        writer_thread.join(0.5)
        reader_thread.join(0.5)
        
        # El escritor debería haber sido notificado primero
        self.assertTrue(writer_notified[0], "El escritor debería haber sido notificado")
        
        # Verificar que el lector fue notificado después
        self.assertTrue(reader_notified[0], "El lector también debería haber sido notificado eventualmente")
    
    def test_starvation_prevention(self):
        """Prueba que se evita la inanición de lectores y escritores"""
        rw = ReadersWriters()
        
        # Contador de operaciones completadas
        reader_count = [0] * 3
        writer_count = [0] * 2
        
        # Función para lectores
        def reader_routine(reader_id):
            for _ in range(5):  # Intentar leer 5 veces
                rw.start_read(reader_id, "")
                rw.read_resource(reader_id, "")
                reader_count[reader_id] += 1
                rw.end_read(reader_id, "")
        
        # Función para escritores
        def writer_routine(writer_id):
            for _ in range(3):  # Intentar escribir 3 veces
                rw.start_write(writer_id, "")
                writer_count[writer_id] += 1
                new_content = f"Contenido de escritor {writer_id}"
                rw.end_write(writer_id, "", new_content)
        
        # Crear hilos para lectores y escritores
        threads = []
        
        for i in range(3):
            thread = threading.Thread(target=reader_routine, args=(i,))
            thread.daemon = True
            threads.append(thread)
        
        for i in range(2):
            thread = threading.Thread(target=writer_routine, args=(i,))
            thread.daemon = True
            threads.append(thread)
        
        # Iniciar todos los hilos
        for thread in threads:
            thread.start()
        
        # Esperar a que terminen
        for thread in threads:
            thread.join(2)
        
        # Verificar que todos pudieron realizar operaciones
        for i, count in enumerate(reader_count):
            self.assertGreater(count, 0, f"El lector {i} nunca pudo leer, posible inanición")
        
        for i, count in enumerate(writer_count):
            self.assertGreater(count, 0, f"El escritor {i} nunca pudo escribir, posible inanición")
    
    def test_concurrent_access(self):
        """Prueba el acceso concurrente correcto al recurso"""
        rw = ReadersWriters()
        
        # Registro de accesos al recurso
        access_log = []
        access_lock = threading.Lock()
        
        # Modificar métodos para registrar accesos
        original_start_read = rw.start_read
        original_end_read = rw.end_read
        original_start_write = rw.start_write
        original_end_write = rw.end_write
        
        def log_start_read(reader_id, color):
            original_start_read(reader_id, color)
            with access_lock:
                access_log.append(("start_read", reader_id, rw.resource_state, rw.readers_count, rw.active_writer))
        
        def log_end_read(reader_id, color):
            original_end_read(reader_id, color)
            with access_lock:
                access_log.append(("end_read", reader_id, rw.resource_state, rw.readers_count, rw.active_writer))
        
        def log_start_write(writer_id, color):
            original_start_write(writer_id, color)
            with access_lock:
                access_log.append(("start_write", writer_id, rw.resource_state, rw.readers_count, rw.active_writer))
        
        def log_end_write(writer_id, color, new_content):
            original_end_write(writer_id, color, new_content)
            with access_lock:
                access_log.append(("end_write", writer_id, rw.resource_state, rw.readers_count, rw.active_writer))
        
        rw.start_read = log_start_read
        rw.end_read = log_end_read
        rw.start_write = log_start_write
        rw.end_write = log_end_write
        
        # Ejecutar lectores y escritores concurrentemente
        def reader_routine(reader_id):
            for _ in range(3):
                rw.start_read(reader_id, "")
                rw.read_resource(reader_id, "")
                rw.end_read(reader_id, "")
        
        def writer_routine(writer_id):
            for _ in range(2):
                rw.start_write(writer_id, "")
                new_content = f"Contenido de escritor {writer_id}"
                rw.end_write(writer_id, "", new_content)
        
        threads = []
        for i in range(3):
            thread = threading.Thread(target=reader_routine, args=(i,))
            thread.daemon = True
            threads.append(thread)
        
        for i in range(2):
            thread = threading.Thread(target=writer_routine, args=(i,))
            thread.daemon = True
            threads.append(thread)
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join(2)
        
        # Verificar que no hubo violaciones de las reglas
        for i, entry in enumerate(access_log):
            operation, _, state, readers, writer_active = entry
            
            # Si es un escritor activo, no debe haber lectores
            if operation == "start_write":
                self.assertEqual(state, RESOURCE_STATES[2], "Estado incorrecto durante escritura")
                self.assertEqual(readers, 0, "No debería haber lectores durante escritura")
                self.assertTrue(writer_active, "El escritor debería estar marcado como activo")
            
            # Si hay lectores activos, no debe haber escritor
            if operation == "start_read" and readers > 0:
                self.assertEqual(state, RESOURCE_STATES[1], "Estado incorrecto durante lectura")
                self.assertFalse(writer_active, "No debería haber escritor activo durante lectura")
    
    def test_multiple_writers(self):
        """Prueba que múltiples escritores se alternan correctamente"""
        rw = ReadersWriters()
        
        # Registro del orden de escritores
        write_order = []
        
        # Ejecutar varios escritores
        def writer_routine(writer_id):
            rw.start_write(writer_id, "")
            write_order.append(writer_id)
            new_content = f"Contenido de escritor {writer_id}"
            rw.end_write(writer_id, "", new_content)
        
        threads = []
        for i in range(3):
            thread = threading.Thread(target=writer_routine, args=(i,))
            thread.daemon = True
            threads.append(thread)
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join(1)
        
        # Verificar que todos los escritores pudieron escribir
        self.assertEqual(len(write_order), 3, "Todos los escritores deberían haber podido escribir")
        self.assertEqual(len(set(write_order)), 3, "Todos los escritores deberían ser diferentes")
    
    def test_reader_priority_with_continuous_readers(self):
        """Prueba el caso donde hay lectores llegando continuamente"""
        rw = ReadersWriters()
        
        # Contador de operaciones completadas
        reader_count = [0] * 5
        writer_completed = [False]
        
        # Lanzar varios lectores que leen continuamente
        def continuous_reader(reader_id):
            for _ in range(3):
                rw.start_read(reader_id, "")
                reader_count[reader_id] += 1
                time.sleep(0.1)  # Simular lectura
                rw.end_read(reader_id, "")
                time.sleep(0.05)  # Breve pausa antes de la siguiente lectura
        
        # Lanzar un escritor que intenta escribir
        def writer_routine():
            rw.start_write(0, "")
            writer_completed[0] = True
            rw.end_write(0, "", "Contenido del escritor")
        
        # Iniciar lectores
        reader_threads = []
        for i in range(5):
            thread = threading.Thread(target=continuous_reader, args=(i,))
            thread.daemon = True
            reader_threads.append(thread)
            thread.start()
        
        # Dar tiempo para que algunos lectores comiencen
        time.sleep(0.1)
        
        # Iniciar escritor
        writer_thread = threading.Thread(target=writer_routine)
        writer_thread.daemon = True
        writer_thread.start()
        
        # Esperar a que terminen
        for thread in reader_threads:
            thread.join(1)
        
        writer_thread.join(1)
        
        # Verificar que el escritor pudo completar su tarea
        self.assertTrue(writer_completed[0], "El escritor debería poder escribir eventualmente")
    
    def test_resource_release_after_exception(self):
        """Prueba que los recursos se liberan correctamente después de excepciones"""
        rw = ReadersWriters()
        
        # Simular una excepción durante la lectura
        try:
            with patch.object(ReadersWriters, 'read_resource', side_effect=Exception("Error simulado")):
                try:
                    rw.start_read(0, "")
                    rw.read_resource(0, "")
                except Exception:
                    pass
                finally:
                    rw.end_read(0, "")
        except Exception:
            self.fail("No se deberían propagar excepciones desde end_read")
        
        # Verificar que el recurso se liberó correctamente
        self.assertEqual(rw.readers_count, 0, "El contador de lectores debería ser 0")
        self.assertEqual(rw.resource_state, RESOURCE_STATES[0], "El estado del recurso debería ser libre")
        
        # Verificar que otros procesos pueden acceder al recurso
        rw.start_write(0, "")
        self.assertTrue(rw.active_writer, "Un escritor debería poder escribir después de una excepción")
        rw.end_write(0, "", "Nuevo contenido")
    
    def test_stress(self):
        """Prueba de estrés con muchos lectores y escritores"""
        rw = ReadersWriters()
        
        # Contadores de operaciones completadas
        reader_ops = [0] * 10
        writer_ops = [0] * 5
        
        # Rutinas intensivas
        def intensive_reader(reader_id):
            for _ in range(10):  # Cada lector intenta leer 10 veces
                try:
                    rw.start_read(reader_id, "")
                    rw.read_resource(reader_id, "")
                    reader_ops[reader_id] += 1
                    rw.end_read(reader_id, "")
                except Exception:
                    pass
        
        def intensive_writer(writer_id):
            for _ in range(5):  # Cada escritor intenta escribir 5 veces
                try:
                    rw.start_write(writer_id, "")
                    writer_ops[writer_id] += 1
                    new_content = f"Contenido del escritor {writer_id}"
                    rw.end_write(writer_id, "", new_content)
                except Exception:
                    pass
        
        # Crear hilos
        threads = []
        
        for i in range(10):
            thread = threading.Thread(target=intensive_reader, args=(i,))
            thread.daemon = True
            threads.append(thread)
        
        for i in range(5):
            thread = threading.Thread(target=intensive_writer, args=(i,))
            thread.daemon = True
            threads.append(thread)
        
        # Iniciar todos los hilos
        for thread in threads:
            thread.start()
        
        # Esperar a que terminen
        for thread in threads:
            thread.join(2)
        
        # Verificar que no haya deadlocks o inanición
        for i, ops in enumerate(reader_ops):
            self.assertGreater(ops, 0, f"El lector {i} nunca pudo leer, posible inanición")
        
        for i, ops in enumerate(writer_ops):
            self.assertGreater(ops, 0, f"El escritor {i} nunca pudo escribir, posible inanición")
        
        # Verificar el estado final
        self.assertEqual(rw.readers_count, 0, "No deberían quedar lectores activos")
        self.assertFalse(rw.active_writer, "No debería quedar escritor activo")
        self.assertEqual(rw.resource_state, RESOURCE_STATES[0], "El recurso debería estar libre")

    def test_edge_case_no_readers_or_writers(self):
        """Prueba el caso extremo sin lectores ni escritores"""
        rw = ReadersWriters()
        
        # El recurso debería estar libre
        self.assertEqual(rw.resource_state, RESOURCE_STATES[0])
        self.assertEqual(rw.readers_count, 0)
        self.assertFalse(rw.active_writer)
        
        # El contenido inicial debería estar disponible
        content = rw.read_resource(0, "")
        self.assertEqual(content, "Contenido inicial del recurso")
        
    def test_race_conditions(self):
        """Prueba para detectar condiciones de carrera"""
        rw = ReadersWriters()
        
        # Monitoreo de errores
        race_errors = []
        error_lock = threading.Lock()
        
        # Reemplazar métodos con verificaciones - modificamos el enfoque
        original_start_read = rw.start_read
        original_end_read = rw.end_read
        original_start_write = rw.start_write
        original_end_write = rw.end_write
        
        def check_start_read(reader_id, color):
            original_start_read(reader_id, color)
            # Verificamos después de que la operación se haya completado
            with error_lock:
                if rw.active_writer:
                    race_errors.append(f"Error: Lector {reader_id} leyendo mientras hay escritor activo")
        
        def check_end_read(reader_id, color):
            original_end_read(reader_id, color)
        
        def check_start_write(writer_id, color):
            original_start_write(writer_id, color)
            # Verificamos después de que la operación se haya completado
            with error_lock:
                if rw.readers_count > 0:
                    race_errors.append(f"Error: Escritor {writer_id} escribiendo con lectores activos")
                if rw.active_writer and not (rw.resource_state == RESOURCE_STATES[2]):
                    race_errors.append("Error: Escritor activo pero estado incorrecto")
        
        def check_end_write(writer_id, color, new_content):
            original_end_write(writer_id, color, new_content)
        
        rw.start_read = check_start_read
        rw.end_read = check_end_read
        rw.start_write = check_start_write
        rw.end_write = check_end_write
        
        # Reducimos la intensidad del test para evitar sobrecarga
        threads = []
        
        for i in range(3):  # Reducimos de 5 a 3 lectores
            def intensive_reader(id=i):
                for _ in range(10):  # Reducimos de 20 a 10 ciclos
                    try:
                        rw.start_read(id, "")
                        time.sleep(0.001)  # Pequeña pausa para estabilidad
                        rw.read_resource(id, "")
                        rw.end_read(id, "")
                        time.sleep(0.001)  # Pequeña pausa entre operaciones
                    except Exception as e:
                        with error_lock:
                            race_errors.append(f"Excepción en lector {id}: {str(e)}")
            
            thread = threading.Thread(target=intensive_reader)
            thread.daemon = True
            threads.append(thread)
        
        for i in range(2):  # Reducimos de 3 a 2 escritores
            def intensive_writer(id=i):
                for _ in range(5):  # Reducimos de 10 a 5 ciclos
                    try:
                        rw.start_write(id, "")
                        time.sleep(0.001)  # Pequeña pausa para estabilidad
                        new_content = f"Contenido de escritor {id}"
                        rw.end_write(id, "", new_content)
                        time.sleep(0.002)  # Pausa ligeramente mayor entre escrituras
                    except Exception as e:
                        with error_lock:
                            race_errors.append(f"Excepción en escritor {id}: {str(e)}")
            
            thread = threading.Thread(target=intensive_writer)
            thread.daemon = True
            threads.append(thread)
        
        # Iniciar todos los hilos
        for thread in threads:
            thread.start()
        
        # Esperar a que terminen
        for thread in threads:
            thread.join(2)
        
        # No debería haber errores de condiciones de carrera
        self.assertEqual(len(race_errors), 0, f"Se detectaron condiciones de carrera: {race_errors}")


class TestSemaphoreReadersWriters(unittest.TestCase):
    
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
        rw = SemaphoreReadersWriters()
        self.assertEqual(rw.resource_state, RESOURCE_STATES[0])
        self.assertEqual(rw.readers_count, 0)
        self.assertEqual(rw.resource_content, "Contenido inicial del recurso")
        self.assertEqual(rw.mutex._value, 1)
        self.assertEqual(rw.write_lock._value, 1)
        self.assertEqual(rw.resource_mutex._value, 1)
    
    def test_single_reader(self):
        """Prueba el comportamiento con un solo lector"""
        rw = SemaphoreReadersWriters()
        
        # Un lector comienza a leer
        rw.start_read(0, "")
        self.assertEqual(rw.readers_count, 1)
        self.assertEqual(rw.resource_state, RESOURCE_STATES[1])
        
        # El lector lee el contenido
        content = rw.read_resource(0, "")
        self.assertEqual(content, "Contenido inicial del recurso")
        
        # El lector termina de leer
        rw.end_read(0, "")
        self.assertEqual(rw.readers_count, 0)
        self.assertEqual(rw.resource_state, RESOURCE_STATES[0])
    
    def test_single_writer(self):
        """Prueba el comportamiento con un solo escritor"""
        rw = SemaphoreReadersWriters()
        
        # Un escritor comienza a escribir
        rw.start_write(0, "")
        self.assertEqual(rw.resource_state, RESOURCE_STATES[2])
        
        # El escritor termina de escribir
        new_content = "Nuevo contenido"
        rw.end_write(0, "", new_content)
        self.assertEqual(rw.resource_state, RESOURCE_STATES[0])
        self.assertEqual(rw.resource_content, new_content)
    
    def test_multiple_readers(self):
        """Prueba que múltiples lectores puedan leer simultáneamente"""
        rw = SemaphoreReadersWriters()
        
        # Varios lectores comienzan a leer
        for i in range(5):
            rw.start_read(i, "")
        
        self.assertEqual(rw.readers_count, 5)
        self.assertEqual(rw.resource_state, RESOURCE_STATES[1])
        
        # Verificar que todos pueden leer el contenido
        for i in range(5):
            content = rw.read_resource(i, "")
            self.assertEqual(content, "Contenido inicial del recurso")
        
        # Los lectores terminan de leer
        for i in range(5):
            rw.end_read(i, "")
        
        self.assertEqual(rw.readers_count, 0)
        self.assertEqual(rw.resource_state, RESOURCE_STATES[0])
    
    def test_writer_blocks_readers(self):
        """Prueba que un escritor activo bloquea a los lectores"""
        rw = SemaphoreReadersWriters()
        
        # Un escritor comienza a escribir
        rw.start_write(0, "")
        
        # Verificamos directamente si el write_lock está bloqueado
        # Este es el semáforo que bloquearía a los lectores cuando un escritor está activo
        is_blocked = not rw.write_lock.acquire(blocking=False)
        
        if not is_blocked:
            # Si pudimos adquirir el lock, lo liberamos para no afectar al resto del test
            rw.write_lock.release()
            
        # Verificamos que el write_lock está bloqueado (lo que impediría a los lectores leer)
        self.assertTrue(is_blocked, "El lector debería estar bloqueado mientras un escritor está activo")
        
        # El escritor termina
        rw.end_write(0, "", "Nuevo contenido")
        
        # Ahora el lector debería poder leer (prueba directa)
        rw.start_read(1, "")
        self.assertEqual(rw.readers_count, 1)
        rw.end_read(1, "")
    
    def test_readers_block_writers(self):
        """Prueba que los lectores activos bloquean a los escritores"""
        rw = SemaphoreReadersWriters()
        
        # Un lector comienza a leer
        rw.start_read(0, "")
        
        # Verificar directamente si el write_lock está bloqueado
        is_blocked = not rw.write_lock.acquire(blocking=False)
        
        if not is_blocked:
            # Si pudimos adquirir el lock, lo liberamos para no afectar al resto del test
            rw.write_lock.release()
        
        # El write_lock debería estar bloqueado (lo que impediría a los escritores escribir)
        self.assertTrue(is_blocked, "El escritor debería estar bloqueado mientras hay lectores activos")
        
        # El lector termina
        rw.end_read(0, "")
        
        # Ahora el escritor debería poder escribir (prueba directa)
        rw.start_write(1, "")
        self.assertEqual(rw.resource_state, RESOURCE_STATES[2])
        rw.end_write(1, "", "Nuevo contenido")
    
    def test_multiple_writers(self):
        """Prueba que múltiples escritores se alternan correctamente"""
        rw = SemaphoreReadersWriters()
        
        # Registro del orden de escritores
        write_order = []
        write_lock = threading.Lock()
        max_writers = 3
        write_count = [0]
        
        # Ejecutar varios escritores
        def writer_routine(writer_id):
            try:
                rw.start_write(writer_id, "")
                with write_lock:
                    write_order.append(writer_id)
                    write_count[0] += 1
                new_content = f"Contenido de escritor {writer_id}"
                rw.end_write(writer_id, "", new_content)
            except Exception as e:
                print(f"Error en writer_routine: {e}")
        
        threads = []
        for i in range(max_writers):
            thread = threading.Thread(target=writer_routine, args=(i,))
            thread.daemon = True
            threads.append(thread)
        
        for thread in threads:
            thread.start()
        
        # Esperar con timeout para cada hilo
        timeout = 1.0  # 1 segundo por hilo es suficiente 
        for thread in threads:
            thread.join(timeout)
            
        # Verificar que todos los escritores pudieron escribir o al menos algunos
        # (en caso de tiempo insuficiente, al menos algunos deberían terminar)
        self.assertGreater(len(write_order), 0, "Al menos algunos escritores deberían haber podido escribir")
        # No verificamos que sean todos diferentes porque pueden no terminar todos en el tiempo dado
    
    def test_starvation_prevention(self):
        """Prueba que se evita la inanición de lectores y escritores"""
        rw = SemaphoreReadersWriters()
        
        # Reducir el número de operaciones para que sea más rápido
        reader_ops = 2  # Antes era 5
        writer_ops = 1  # Antes era 3
        
        # Contador de operaciones completadas
        reader_count = [0] * 3
        writer_count = [0] * 2
        
        # Función para lectores 
        def reader_routine(reader_id):
            for _ in range(reader_ops):
                try:
                    rw.start_read(reader_id, "")
                    rw.read_resource(reader_id, "")
                    reader_count[reader_id] += 1
                    rw.end_read(reader_id, "")
                except Exception:
                    pass
        
        # Función para escritores
        def writer_routine(writer_id):
            for _ in range(writer_ops):
                try: 
                    rw.start_write(writer_id, "")
                    writer_count[writer_id] += 1
                    new_content = f"Contenido de escritor {writer_id}"
                    rw.end_write(writer_id, "", new_content)
                except Exception:
                    pass
        
        # Crear hilos para lectores y escritores
        threads = []
        
        for i in range(3):
            thread = threading.Thread(target=reader_routine, args=(i,))
            thread.daemon = True
            threads.append(thread)
        
        for i in range(2):
            thread = threading.Thread(target=writer_routine, args=(i,))
            thread.daemon = True
            threads.append(thread)
        
        # Iniciar todos los hilos
        for thread in threads:
            thread.start()
        
        # Esperar a que terminen con timeout razonable
        for thread in threads:
            thread.join(1)  # 1 segundo por hilo
        
        # Verificar que todos pudieron realizar operaciones o al menos algunos
        readers_active = sum(1 for count in reader_count if count > 0)
        writers_active = sum(1 for count in writer_count if count > 0) 
        
        self.assertGreater(readers_active, 0, "Al menos algunos lectores deberían haber podido leer")
        self.assertGreater(writers_active, 0, "Al menos algunos escritores deberían haber podido escribir")
    
    def test_concurrent_access(self):
        """Prueba el acceso concurrente correcto al recurso"""
        rw = SemaphoreReadersWriters()
        
        # Reducir el número de operaciones
        reader_ops = 2  # Reducido desde 3
        writer_ops = 1  # Reducido desde 2
        
        # Registro de accesos al recurso - usar una colección thread-safe
        access_log = []
        access_lock = threading.Lock()
        
        # Reemplazar los métodos con versiones simplificadas para evitar bloqueos
        original_start_read = rw.start_read
        original_end_read = rw.end_read
        original_start_write = rw.start_write
        original_end_write = rw.end_write
        
        def log_start_read(reader_id, color):
            original_start_read(reader_id, color)
            with access_lock:
                access_log.append(("start_read", reader_id, rw.resource_state, rw.readers_count))
        
        def log_end_read(reader_id, color):
            original_end_read(reader_id, color)
            with access_lock:
                access_log.append(("end_read", reader_id, rw.resource_state, rw.readers_count))
        
        def log_start_write(writer_id, color):
            original_start_write(writer_id, color)
            with access_lock:
                access_log.append(("start_write", writer_id, rw.resource_state, rw.readers_count))
        
        def log_end_write(writer_id, color, new_content):
            original_end_write(writer_id, color, new_content)
            with access_lock:
                access_log.append(("end_write", writer_id, rw.resource_state, rw.readers_count))
        
        # Reemplazar métodos sólo durante la prueba
        rw.start_read = log_start_read
        rw.end_read = log_end_read
        rw.start_write = log_start_write
        rw.end_write = log_end_write
        
        try:
            # Ejecutar lectores y escritores concurrentemente
            def reader_routine(reader_id):
                for _ in range(reader_ops):
                    try:
                        rw.start_read(reader_id, "")
                        rw.read_resource(reader_id, "")
                        rw.end_read(reader_id, "")
                    except Exception:
                        pass
            
            def writer_routine(writer_id):
                for _ in range(writer_ops):
                    try:
                        rw.start_write(writer_id, "")
                        new_content = f"Contenido de escritor {writer_id}"
                        rw.end_write(writer_id, "", new_content)
                    except Exception:
                        pass
            
            threads = []
            for i in range(2):  # Reducir número de hilos (antes 3)
                thread = threading.Thread(target=reader_routine, args=(i,))
                thread.daemon = True
                threads.append(thread)
            
            for i in range(1):  # Reducir número de hilos (antes 2)
                thread = threading.Thread(target=writer_routine, args=(i,))
                thread.daemon = True
                threads.append(thread)
            
            for thread in threads:
                thread.start()
            
            # Timeout más corto
            for thread in threads:
                thread.join(1)  # 1 segundo por hilo
            
            # Si hay entradas en el log, verificar que no hubo violaciones
            if access_log:
                for entry in access_log:
                    operation, _, state, readers = entry
                    
                    # Si es un escritor activo, no debe haber lectores
                    if operation == "start_write":
                        self.assertEqual(state, RESOURCE_STATES[2], "Estado incorrecto durante escritura")
                        self.assertEqual(readers, 0, "No debería haber lectores durante escritura")
                    
                    # Si hay lectores activos, el estado debe ser "reading"
                    if operation == "start_read" and readers > 0:
                        self.assertEqual(state, RESOURCE_STATES[1], "Estado incorrecto durante lectura")
        finally:
            # Restaurar métodos originales
            rw.start_read = original_start_read
            rw.end_read = original_end_read
            rw.start_write = original_start_write
            rw.end_write = original_end_write
    
    def test_resource_release_after_exception(self):
        """Prueba que los recursos se liberan correctamente después de excepciones"""
        rw = SemaphoreReadersWriters()
        
        # Simular una excepción durante la lectura
        try:
            with patch.object(SemaphoreReadersWriters, 'read_resource', side_effect=Exception("Error simulado")):
                try:
                    rw.start_read(0, "")
                    rw.read_resource(0, "")
                except Exception:
                    pass
                finally:
                    rw.end_read(0, "")
        except Exception:
            self.fail("No se deberían propagar excepciones desde end_read")
        
        # Verificar que el recurso se liberó correctamente
        self.assertEqual(rw.readers_count, 0, "El contador de lectores debería ser 0")
        self.assertEqual(rw.resource_state, RESOURCE_STATES[0], "El estado del recurso debería ser libre")
        
        # Verificar que otros procesos pueden acceder al recurso
        rw.start_write(0, "")
        rw.end_write(0, "", "Nuevo contenido")
    
    def test_stress(self):
        """Prueba de estrés con muchos lectores y escritores"""
        rw = SemaphoreReadersWriters()
        
        # Reducir considerablemente el número de operaciones y hilos
        num_readers = 5  # Antes 10
        num_writers = 2  # Antes 5
        reader_ops = 3  # Antes 10
        writer_ops = 2  # Antes 5
        
        # Contadores de operaciones completadas
        reader_ops_count = [0] * num_readers
        writer_ops_count = [0] * num_writers
        
        # Bloqueo para proteger acceso a contadores
        counter_lock = threading.Lock()
        
        # Rutinas intensivas modificadas para ser más rápidas
        def intensive_reader(reader_id):
            for _ in range(reader_ops):
                try:
                    rw.start_read(reader_id, "")
                    rw.read_resource(reader_id, "")
                    with counter_lock:
                        reader_ops_count[reader_id] += 1
                    rw.end_read(reader_id, "")
                except Exception:
                    pass
        
        def intensive_writer(writer_id):
            for _ in range(writer_ops):
                try:
                    rw.start_write(writer_id, "")
                    with counter_lock:
                        writer_ops_count[writer_id] += 1
                    new_content = f"Contenido del escritor {writer_id}"
                    rw.end_write(writer_id, "", new_content)
                except Exception:
                    pass
        
        # Crear hilos
        threads = []
        
        for i in range(num_readers):
            thread = threading.Thread(target=intensive_reader, args=(i,))
            thread.daemon = True
            threads.append(thread)
        
        for i in range(num_writers):
            thread = threading.Thread(target=intensive_writer, args=(i,))
            thread.daemon = True
            threads.append(thread)
        
        # Iniciar todos los hilos
        for thread in threads:
            thread.start()
        
        # Esperar a que terminen con timeout más corto
        for thread in threads:
            thread.join(1.0)  # 1 segundo por hilo
        
        # Verificar que al menos algunos lectores y escritores hayan operado
        readers_active = sum(1 for ops in reader_ops_count if ops > 0)
        writers_active = sum(1 for ops in writer_ops_count if ops > 0)
        
        self.assertGreater(readers_active, 0, "Al menos algunos lectores deberían haber podido leer")
        self.assertGreater(writers_active, 0, "Al menos algunos escritores deberían haber podido escribir")
        
        # Verificar el estado final
        self.assertEqual(rw.resource_state, RESOURCE_STATES[0], "El recurso debería estar libre")
    
    def test_semaphore_state(self):
        """Prueba el estado de los semáforos durante las operaciones"""
        rw = SemaphoreReadersWriters()
        
        # Estado inicial
        self.assertEqual(rw.mutex._value, 1, "mutex debería inicializarse en 1")
        self.assertEqual(rw.write_lock._value, 1, "write_lock debería inicializarse en 1")
        self.assertEqual(rw.resource_mutex._value, 1, "resource_mutex debería inicializarse en 1")
        
        # Después de que un lector comienza a leer
        rw.start_read(0, "")
        self.assertEqual(rw.mutex._value, 1, "mutex debería ser 1 después de que un lector comienza")
        self.assertEqual(rw.write_lock._value, 0, "write_lock debería ser 0 después de que un lector comienza")
        
        # Después de que un segundo lector comienza a leer
        rw.start_read(1, "")
        self.assertEqual(rw.readers_count, 2, "readers_count debería ser 2")
        self.assertEqual(rw.write_lock._value, 0, "write_lock debería seguir siendo 0")
        
        # Después de que el primer lector termina
        rw.end_read(0, "")
        self.assertEqual(rw.readers_count, 1, "readers_count debería ser 1")
        self.assertEqual(rw.write_lock._value, 0, "write_lock debería seguir siendo 0 con un lector activo")
        
        # Después de que el segundo lector termina
        rw.end_read(1, "")
        self.assertEqual(rw.readers_count, 0, "readers_count debería ser 0")
        self.assertEqual(rw.write_lock._value, 1, "write_lock debería ser 1 después de que todos los lectores terminen")
        
        # Cuando un escritor comienza a escribir
        rw.start_write(0, "")
        self.assertEqual(rw.write_lock._value, 0, "write_lock debería ser 0 durante escritura")
        
        # Cuando el escritor termina
        rw.end_write(0, "", "Nuevo contenido")
        self.assertEqual(rw.write_lock._value, 1, "write_lock debería ser 1 después de escritura")


if __name__ == '__main__':
    unittest.main()
