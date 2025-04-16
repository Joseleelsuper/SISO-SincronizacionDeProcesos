import threading
import time
import random

try:
    from src.utils.colors import COLORS, RESET
except ImportError:
    from utils.colors import COLORS, RESET

# Definición de las variables compartidas
flag = [False, False]  # Indica si un proceso quiere entrar a la sección crítica
turn = 0  # Indica a quién le toca entrar a la sección crítica en caso de conflicto

# Variables para simulación
shared_resource = 0  # Recurso compartido que los procesos van a modificar
ITERATIONS = 5  # Número de iteraciones que cada proceso ejecutará
MIN_WORK_TIME = 1  # Tiempo mínimo de trabajo en la sección crítica
MAX_WORK_TIME = 3  # Tiempo máximo de trabajo en la sección crítica
MIN_REST_TIME = 1  # Tiempo mínimo de descanso entre iteraciones
MAX_REST_TIME = 2  # Tiempo máximo de descanso entre iteraciones

class DekkerProcess(threading.Thread):
    """
    Implementación de un proceso usando el algoritmo de Dekker para exclusión mutua.
    """
    
    def __init__(self, process_id, color):
        """
        Inicializa un proceso con un ID y un color para mensajes.
        
        Args:
            process_id (int): ID del proceso (0 o 1)
            color (str): Color para imprimir mensajes en la consola
        """
        threading.Thread.__init__(self)
        self.process_id = process_id
        self.color = color
        self.other = 1 - process_id  # ID del otro proceso
    
    def run(self):
        """
        Ejecuta el proceso varias veces, usando el algoritmo de Dekker para
        acceder a la sección crítica.
        """
        global shared_resource, turn  # Added turn to the global declaration
        
        for i in range(ITERATIONS):
            # Sección de entrada (protocolo de entrada)
            print(f"{self.color}Proceso {self.process_id} quiere entrar a la sección crítica (Iteración {i+1}){RESET}")
            flag[self.process_id] = True  # Indico que quiero entrar
            
            # Espera activa mientras el otro proceso quiera entrar y sea su turno
            while flag[self.other]:
                if turn != self.process_id:
                    # Si no es mi turno, cedo y espero a que me toque
                    flag[self.process_id] = False
                    while turn != self.process_id:
                        # Espera activa hasta que sea mi turno
                        pass
                    flag[self.process_id] = True
            
            # Sección crítica
            print(f"{self.color}Proceso {self.process_id} entra a la sección crítica{RESET}")
            # Simular trabajo en la sección crítica
            work_time = random.randint(MIN_WORK_TIME, MAX_WORK_TIME)
            print(f"{self.color}Proceso {self.process_id} trabajando durante {work_time} segundos{RESET}")
            
            # Modificar el recurso compartido
            local_resource = shared_resource
            # Simular algún procesamiento
            time.sleep(work_time)
            shared_resource = local_resource + 1
            print(f"{self.color}Proceso {self.process_id} modifica el recurso: {shared_resource}{RESET}")
            
            # Sección de salida (protocolo de salida)
            turn = self.other  # Ceder el turno al otro proceso
            flag[self.process_id] = False  # Indicar que he terminado
            print(f"{self.color}Proceso {self.process_id} sale de la sección crítica{RESET}")
            
            # Sección restante (trabajo fuera de la sección crítica)
            rest_time = random.randint(MIN_REST_TIME, MAX_REST_TIME)
            print(f"{self.color}Proceso {self.process_id} descansando por {rest_time} segundos{RESET}")
            time.sleep(rest_time)

def main():
    """
    Función principal para iniciar la simulación del algoritmo de Dekker.
    Crea dos procesos que compiten por acceder a un recurso compartido.
    """
    # Crear los procesos
    process0 = DekkerProcess(0, COLORS[0])
    process1 = DekkerProcess(1, COLORS[1])
    
    # Iniciar los procesos
    process0.start()
    process1.start()
    
    # Esperar a que terminen
    process0.join()
    process1.join()
    
    print(f"Valor final del recurso compartido: {shared_resource}")
    print(f"Valor esperado (cada proceso incrementa {ITERATIONS} veces): {ITERATIONS * 2}")
    
    # Verificar si hubo algún problema de exclusión mutua
    if shared_resource != ITERATIONS * 2:
        print("¡ADVERTENCIA! Posible problema de exclusión mutua detectado.")
    else:
        print("La exclusión mutua funcionó correctamente.")

if __name__ == "__main__":
    """
    PROBLEMAS DEL ALGORITMO DE DEKKER:
    
    1. Espera activa (busy waiting): El algoritmo utiliza espera activa, lo que consume
       CPU innecesariamente mientras un proceso espera su turno.
    
    2. Limitado a 2 procesos: El algoritmo sólo funciona para exactamente dos procesos,
       no es escalable a más procesos sin modificaciones significativas.
    
    3. Reordenamiento de instrucciones: En CPUs modernas, las instrucciones pueden 
       reordenarse por optimización. Esto puede romper la lógica del algoritmo, ya que
       asume un orden específico de ejecución de las instrucciones.
    
    4. Visibilidad de cambios: En sistemas multiprocesador, los cambios a variables
       compartidas realizados por un procesador pueden no ser visibles inmediatamente
       para otro, lo que podría causar inconsistencias.
    
    5. Falta de garantías de atomicidad: Python no garantiza que operaciones como
       asignaciones sean atómicas en entornos multihilo, lo que puede llevar a
       comportamientos inesperados.
    
    6. Posible inanición (starvation): Si un proceso es interrumpido después de
       establecer su bandera pero antes de verificar su turno, y el otro proceso
       se ejecuta frecuentemente, podría darse una situación de inanición.
    
    7. Sobrecarga de comunicación: El algoritmo requiere múltiples operaciones de
       lectura y escritura en memoria compartida, lo que puede ser ineficiente.
    
    8. En Python específicamente, el GIL (Global Interpreter Lock) puede afectar
       el comportamiento de los hilos, haciendo que este ejemplo no refleje
       completamente las condiciones de carrera que ocurrirían en un entorno real
       con verdadero paralelismo.
    """
    main()
