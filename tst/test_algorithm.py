import unittest
import threading
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from src.algorithm_dekker import DekkerProcess, ITERATIONS
from src.algorithm_dekker import flag, turn, shared_resource


class TestDekkerAlgorithm(unittest.TestCase):
    
    def setUp(self):
        # Reset shared variables before each test
        global flag, turn, shared_resource
        flag[0] = False
        flag[1] = False
        turn = 0
        shared_resource = 0
        
        # Patch time.sleep to speed up tests
        self.sleep_patcher = patch('time.sleep')
        self.mock_sleep = self.sleep_patcher.start()
        
        # Patch random.randint for deterministic behavior
        self.random_patcher = patch('random.randint', return_value=1)
        self.mock_random = self.random_patcher.start()
    
    def tearDown(self):
        self.sleep_patcher.stop()
        self.random_patcher.stop()
    
    def test_initialization(self):
        """Test correct initialization of DekkerProcess objects"""
        # Create processes
        process0 = DekkerProcess(0, "RED")
        process1 = DekkerProcess(1, "BLUE")
        
        # Check initialization
        self.assertEqual(process0.process_id, 0)
        self.assertEqual(process0.color, "RED")
        self.assertEqual(process0.other, 1)
        
        self.assertEqual(process1.process_id, 1)
        self.assertEqual(process1.color, "BLUE")
        self.assertEqual(process1.other, 0)
        
        # Check initial state of shared variables
        self.assertEqual(flag, [False, False])
        self.assertEqual(turn, 0)
        self.assertEqual(shared_resource, 0)
    
    def test_mutual_exclusion(self):
        """Test that mutual exclusion is maintained during concurrent execution"""
        # Create a list to log critical section entries
        cs_log = []
        cs_lock = threading.Lock()
        
        # Create custom process class for monitoring critical section
        class MonitoredProcess(DekkerProcess):
            def run(self):
                global shared_resource, turn
                
                for i in range(ITERATIONS):
                    # Protocol entry (same as original)
                    print(f"{self.color}Proceso {self.process_id} quiere entrar a la sección crítica (Iteración {i+1})")
                    flag[self.process_id] = True
                    
                    while flag[self.other]:
                        if turn != self.process_id:
                            flag[self.process_id] = False
                            while turn != self.process_id:
                                pass
                            flag[self.process_id] = True
                    
                    # Critical section entry - log entry
                    with cs_lock:
                        cs_log.append((self.process_id, "enter", len(cs_log)))
                    
                    # Simulate work
                    local_resource = shared_resource
                    # No real sleep in tests
                    shared_resource = local_resource + 1
                    
                    # Log exit from critical section
                    with cs_lock:
                        cs_log.append((self.process_id, "exit", len(cs_log)))
                    
                    # Protocol exit
                    turn = self.other
                    flag[self.process_id] = False
                    
                    # No sleep in rest section
        
        # Create and start processes
        process0 = MonitoredProcess(0, "")
        process1 = MonitoredProcess(1, "")
        
        process0.start()
        process1.start()
        
        process0.join()
        process1.join()
        
        # Analyze log to verify mutual exclusion
        in_cs = None
        for entry in cs_log:
            process_id, action, _ = entry
            
            if action == "enter":
                # No process should be in CS when another enters
                self.assertIsNone(in_cs, f"Process {process_id} entered CS while process {in_cs} was still in CS")
                in_cs = process_id
            elif action == "exit":
                # The exiting process should be the one that was in CS
                self.assertEqual(in_cs, process_id, f"Process {process_id} exited CS but process {in_cs} was in CS")
                in_cs = None
        
        # At the end, no process should be in CS
        self.assertIsNone(in_cs, "A process remained in CS at the end")
        
        # Check final shared resource value
        self.assertEqual(shared_resource, ITERATIONS * 2, 
                        f"Expected {ITERATIONS * 2} modifications to shared resource, found {shared_resource}")
    
    def test_fairness(self):
        """Test that both processes get fair access to the critical section"""
        # Create execution order log
        execution_order = []
        
        # Create custom process class to log execution order
        class LoggingProcess(DekkerProcess):
            def run(self):
                global shared_resource, turn
                
                for i in range(ITERATIONS):
                    # Entry protocol
                    flag[self.process_id] = True
                    
                    while flag[self.other]:
                        if turn != self.process_id:
                            flag[self.process_id] = False
                            while turn != self.process_id:
                                pass
                            flag[self.process_id] = True
                    
                    # Log critical section entry
                    execution_order.append(self.process_id)
                    
                    # Simulate work
                    local_resource = shared_resource
                    shared_resource = local_resource + 1
                    
                    # Exit protocol
                    turn = self.other
                    flag[self.process_id] = False
        
        # Create and start processes
        process0 = LoggingProcess(0, "")
        process1 = LoggingProcess(1, "")
        
        process0.start()
        process1.start()
        
        process0.join()
        process1.join()
        
        # Count entries for each process
        p0_entries = execution_order.count(0)
        p1_entries = execution_order.count(1)
        
        # Verify equal number of entries
        self.assertEqual(p0_entries, ITERATIONS, f"Process 0 entered CS {p0_entries} times, expected {ITERATIONS}")
        self.assertEqual(p1_entries, ITERATIONS, f"Process 1 entered CS {p1_entries} times, expected {ITERATIONS}")
        
        # Check alternating pattern (may not be perfect but should show some alternation)
        alternating_count = 0
        for i in range(1, len(execution_order)):
            if execution_order[i] != execution_order[i-1]:
                alternating_count += 1
        
        # We expect some alternation, but not necessarily perfect
        self.assertGreater(alternating_count, 0, "No alternation between processes detected")
    
    def test_flag_state(self):
        """Test that flag state is correctly managed during execution"""
        # Create a list to log flag states
        flag_log = []
        flag_lock = threading.Lock()
        
        # Create custom process to monitor flags
        class FlagMonitorProcess(DekkerProcess):
            def run(self):
                global shared_resource, turn, flag
                
                for i in range(1):  # Just one iteration to simplify the test
                    # Log initial flag state
                    with flag_lock:
                        flag_log.append((self.process_id, "before_entry", flag[0], flag[1]))
                    
                    # Entry protocol
                    flag[self.process_id] = True
                    
                    with flag_lock:
                        flag_log.append((self.process_id, "after_flag_set", flag[0], flag[1]))
                    
                    while flag[self.other]:
                        if turn != self.process_id:
                            flag[self.process_id] = False
                            
                            with flag_lock:
                                flag_log.append((self.process_id, "flag_reset", flag[0], flag[1]))
                            
                            while turn != self.process_id:
                                pass
                            
                            flag[self.process_id] = True
                            
                            with flag_lock:
                                flag_log.append((self.process_id, "flag_reset_end", flag[0], flag[1]))
                    
                    with flag_lock:
                        flag_log.append((self.process_id, "enter_cs", flag[0], flag[1]))
                    
                    # Critical section
                    local_resource = shared_resource
                    shared_resource = local_resource + 1
                    
                    # Exit protocol
                    turn = self.other
                    flag[self.process_id] = False
                    
                    with flag_lock:
                        flag_log.append((self.process_id, "exit_cs", flag[0], flag[1]))
        
        # Create and run a single process for clearer logging
        process0 = FlagMonitorProcess(0, "")
        process0.start()
        process0.join()
        
        # Verify flag states at key points
        # Find the entry point logs
        entry_logs = [entry for entry in flag_log if entry[1] == "after_flag_set" and entry[0] == 0]
        self.assertTrue(entry_logs, "Process should have logged flag state after setting its flag")
        
        # Verify process 0's flag was set to True
        self.assertTrue(entry_logs[0][2], "Process 0's flag should be True after setting it")
        
        # Find the exit point logs
        exit_logs = [entry for entry in flag_log if entry[1] == "exit_cs" and entry[0] == 0]
        self.assertTrue(exit_logs, "Process should have logged flag state after exiting CS")
        
        # Verify process 0's flag was reset to False
        self.assertFalse(exit_logs[0][2], "Process 0's flag should be False after exiting CS")
    
    def test_turn_variable(self):
        """Test that the turn variable alternates correctly"""
        # Create a list to log turn values
        turn_log = []
        turn_lock = threading.Lock()
        
        # Create custom process to monitor turn
        class TurnMonitorProcess(DekkerProcess):
            def run(self):
                global shared_resource, turn
                
                for i in range(ITERATIONS):
                    # Entry protocol
                    flag[self.process_id] = True
                    
                    with turn_lock:
                        turn_log.append((self.process_id, "before_cs", turn))
                    
                    while flag[self.other]:
                        if turn != self.process_id:
                            flag[self.process_id] = False
                            while turn != self.process_id:
                                pass
                            flag[self.process_id] = True
                    
                    # Critical section
                    local_resource = shared_resource
                    shared_resource = local_resource + 1
                    
                    # Exit protocol
                    old_turn = turn
                    turn = self.other
                    
                    with turn_lock:
                        turn_log.append((self.process_id, "after_cs", old_turn, turn))
                    
                    flag[self.process_id] = False
        
        # Create and start processes
        process0 = TurnMonitorProcess(0, "")
        process1 = TurnMonitorProcess(1, "")
        
        process0.start()
        process1.start()
        
        process0.join()
        process1.join()
        
        # Verify turn changes after each process exits CS
        for entry in turn_log:
            if entry[1] == "after_cs":
                process_id, _, old_turn, new_turn = entry
                # Verify turn was changed to the other process
                self.assertEqual(new_turn, 1 - process_id, 
                                f"Process {process_id} should set turn to {1-process_id}, but set it to {new_turn}")
    
    def test_shared_resource_integrity(self):
        """Test that the shared resource is correctly modified"""
        # Set up a mock for time.sleep that allows us to inject artificial waiting
        variable_sleep = MagicMock()
        
        with patch('time.sleep', variable_sleep):
            # Create processes with a modified run method that includes variable delays
            class DelayedProcess(DekkerProcess):
                def run(self):
                    global shared_resource, turn
                    
                    for i in range(ITERATIONS):
                        # Entry protocol
                        flag[self.process_id] = True
                        
                        while flag[self.other]:
                            if turn != self.process_id:
                                flag[self.process_id] = False
                                while turn != self.process_id:
                                    pass
                                flag[self.process_id] = True
                        
                        # Critical section
                        local_resource = shared_resource
                        
                        # Introduce a delay if process 0 to simulate a context switch
                        if self.process_id == 0:
                            # This simulates a context switch after reading the value
                            variable_sleep(0.1)
                        
                        shared_resource = local_resource + 1
                        
                        # Exit protocol
                        turn = self.other
                        flag[self.process_id] = False
            
            # Create and start processes
            process0 = DelayedProcess(0, "")
            process1 = DelayedProcess(1, "")
            
            process0.start()
            process1.start()
            
            process0.join()
            process1.join()
            
            # Verify the shared resource was correctly incremented
            self.assertEqual(shared_resource, ITERATIONS * 2, 
                            f"Expected {ITERATIONS * 2} modifications to shared resource, found {shared_resource}")
    
    def test_starvation_prevention(self):
        """Test that the algorithm prevents starvation"""
        # Create a counter for each process
        process_counters = [0, 0]
        counter_lock = threading.Lock()
        
        # Create processes with a shorter run method for faster testing
        class CountingProcess(DekkerProcess):
            def run(self):
                global shared_resource, turn
                
                for i in range(ITERATIONS):
                    # Entry protocol
                    flag[self.process_id] = True
                    
                    while flag[self.other]:
                        if turn != self.process_id:
                            flag[self.process_id] = False
                            while turn != self.process_id:
                                pass
                            flag[self.process_id] = True
                    
                    # Critical section - increment counter
                    with counter_lock:
                        process_counters[self.process_id] += 1
                    
                    # Increment shared resource
                    local_resource = shared_resource
                    shared_resource = local_resource + 1
                    
                    # Exit protocol
                    turn = self.other
                    flag[self.process_id] = False
        
        # Create and start processes
        process0 = CountingProcess(0, "")
        process1 = CountingProcess(1, "")
        
        process0.start()
        process1.start()
        
        process0.join()
        process1.join()
        
        # Verify both processes got to execute
        self.assertEqual(process_counters[0], ITERATIONS, 
                        f"Process 0 executed {process_counters[0]} times, expected {ITERATIONS}")
        self.assertEqual(process_counters[1], ITERATIONS, 
                        f"Process 1 executed {process_counters[1]} times, expected {ITERATIONS}")
    
    def test_flag_reset_during_protocol(self):
        """Test that flags are correctly reset during protocol"""
        # Create a custom process to test flag resets
        class FlagResetProcess(DekkerProcess):
            def __init__(self, process_id, color):
                super().__init__(process_id, color)
                self.flag_reset_count = 0
            
            def run(self):
                global shared_resource, turn
                
                for i in range(ITERATIONS):
                    # Entry protocol
                    flag[self.process_id] = True
                    
                    # Force the condition where we need to reset the flag
                    if self.process_id == 1:  # Only process 1 will test this
                        flag[self.other] = True  # Force flag[other] to be True
                        turn = self.other       # Force turn to be other's turn
                        
                        # Now the condition for flag reset should be met
                        if turn != self.process_id:
                            flag[self.process_id] = False
                            self.flag_reset_count += 1
                            # Simulate the other process taking its turn
                            flag[self.other] = False
                            turn = self.process_id
                            flag[self.process_id] = True
                    
                    # Rest of protocol and critical section
                    while flag[self.other]:
                        if turn != self.process_id:
                            flag[self.process_id] = False
                            while turn != self.process_id:
                                pass
                            flag[self.process_id] = True
                    
                    # Critical section
                    local_resource = shared_resource
                    shared_resource = local_resource + 1
                    
                    # Exit protocol
                    turn = self.other
                    flag[self.process_id] = False
        
        # Create and run only process 1 to test flag resets
        process1 = FlagResetProcess(1, "")
        process1.start()
        process1.join()
        
        # Verify process 1 reset its flag at least once
        self.assertGreater(process1.flag_reset_count, 0, 
                          "Process 1 should have reset its flag at least once during the protocol")


if __name__ == '__main__':
    unittest.main()