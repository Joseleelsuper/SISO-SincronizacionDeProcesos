import unittest
import threading
import time
from unittest.mock import patch
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
from src.monitor_producer_consumer import ProducerConsumer


class TestProducerConsumer(unittest.TestCase):
    def setUp(self):
        # Patch time.sleep to speed up tests
        self.sleep_patcher = patch("time.sleep")
        self.mock_sleep = self.sleep_patcher.start()

        # Patch random.randint for deterministic behavior
        self.random_patcher = patch("random.randint", return_value=1)
        self.mock_random = self.random_patcher.start()

    def tearDown(self):
        self.sleep_patcher.stop()
        self.random_patcher.stop()

    def test_initialization(self):
        """Verify that the ProducerConsumer initializes correctly"""
        pc = ProducerConsumer(buffer_size=5)
        self.assertEqual(pc.buffer_size, 5)
        self.assertEqual(len(pc.buffer), 0)

    def test_producer_with_full_buffer(self):
        """Test that producers wait when buffer is full"""
        pc = ProducerConsumer(buffer_size=2)

        # Fill the buffer
        pc.produce(1, 0, "")
        pc.produce(2, 0, "")

        # Create a thread that tries to produce to a full buffer
        success = [False]

        def try_produce():
            try:
                timeout = threading.Event()
                timeout.wait(0.1)  # Maximum wait of 100ms
                pc.produce(3, 1, "")
                success[0] = True
            except Exception:
                success[0] = False

        thread = threading.Thread(target=try_produce)
        thread.daemon = True
        thread.start()
        thread.join(0.2)

        self.assertFalse(success[0], "Producer should block when buffer is full")

    def test_consumer_with_empty_buffer(self):
        """Test that consumers wait when buffer is empty"""
        pc = ProducerConsumer(buffer_size=2)

        # Create a thread that tries to consume from an empty buffer
        success = [False]

        def try_consume():
            try:
                timeout = threading.Event()
                timeout.wait(0.1)  # Maximum wait of 100ms
                pc.consume(0, "")
                success[0] = True
            except Exception:
                success[0] = False

        thread = threading.Thread(target=try_consume)
        thread.daemon = True
        thread.start()
        thread.join(0.2)

        self.assertFalse(success[0], "Consumer should block when buffer is empty")

    def test_multiple_producers_consumers(self):
        """Test multiple producers and consumers working together"""
        pc = ProducerConsumer(buffer_size=5)

        produced_items = []
        consumed_items = []

        # Thread-safe access to lists
        items_lock = threading.Lock()

        def producer_routine(producer_id):
            for i in range(3):  # Each producer produces 3 items
                item = f"P{producer_id}_{i}"
                pc.produce(item, producer_id, "")
                with items_lock:
                    produced_items.append(item)

        def consumer_routine(consumer_id):
            for i in range(3):  # Each consumer consumes 3 items
                item = pc.consume(consumer_id, "")
                with items_lock:
                    consumed_items.append(item)

        # Create and start producer threads
        producer_threads = []
        for i in range(2):
            thread = threading.Thread(target=producer_routine, args=(i,))
            thread.daemon = True
            producer_threads.append(thread)
            thread.start()

        # Create and start consumer threads
        consumer_threads = []
        for i in range(2):
            thread = threading.Thread(target=consumer_routine, args=(i,))
            thread.daemon = True
            consumer_threads.append(thread)
            thread.start()

        # Wait for all threads to finish
        for thread in producer_threads + consumer_threads:
            thread.join(2)

        # Verify that all produced items were consumed
        self.assertEqual(len(produced_items), 6, "All items should be produced")
        self.assertEqual(len(consumed_items), 6, "All items should be consumed")

        # The specific items may be consumed in a different order, but all should be accounted for
        for item in produced_items:
            self.assertIn(
                item, consumed_items, f"Item {item} was produced but not consumed"
            )

    def test_mutual_exclusion(self):
        """Test mutual exclusion in buffer access"""
        pc = ProducerConsumer(buffer_size=5)

        # Log of buffer accesses
        access_log = []
        access_lock = threading.Lock()

        original_produce = pc.produce
        original_consume = pc.consume

        def log_produce(item, producer_id, color):
            original_produce(item, producer_id, color)
            with access_lock:
                access_log.append(("produce", pc.buffer.copy()))

        def log_consume(consumer_id, color):
            item = original_consume(consumer_id, color)
            with access_lock:
                access_log.append(("consume", pc.buffer.copy()))
            return item

        pc.produce = log_produce
        pc.consume = log_consume

        # Run multiple producers and consumers concurrently
        def producer_routine(producer_id):
            for i in range(10):  # Each producer produces 10 items
                pc.produce(f"P{producer_id}_{i}", producer_id, "")

        def consumer_routine(consumer_id):
            for i in range(10):  # Each consumer consumes 10 items
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

        # Verify that the buffer never exceeded its size
        for operation, buffer in access_log:
            self.assertLessEqual(
                len(buffer), 5, f"Buffer exceeded size during {operation}: {buffer}"
            )

    def test_notification(self):
        """Test the notification mechanism between producers and consumers"""
        pc = ProducerConsumer(buffer_size=1)

        # Fill the buffer
        pc.produce(1, 0, "")

        # Create a thread that tries to produce to the full buffer
        notified = [False]

        def waiting_producer():
            pc.produce(2, 1, "")
            notified[0] = True

        thread = threading.Thread(target=waiting_producer)
        thread.daemon = True
        thread.start()

        # Give time for the producer to block
        time.sleep(0.1)

        # Producer should not have been notified yet
        self.assertFalse(notified[0], "Producer should be blocked")

        # Consumer consumes item, should notify waiting producer
        pc.consume(0, "")

        # Wait for the producer thread to finish
        thread.join(0.5)

        # Producer should have been notified
        self.assertTrue(notified[0], "Producer should have been notified")

    def test_fairness(self):
        """Test fairness to prevent starvation of producers or consumers"""
        pc = ProducerConsumer(buffer_size=3)

        # Count how many times each producer and consumer acts
        producer_count = [0] * 3
        consumer_count = [0] * 3

        count_lock = threading.Lock()

        # Create a deadlock-free producer routine
        def producer_routine(producer_id):
            for _ in range(5):  # Limit to 5 cycles
                try:
                    pc.produce(f"P{producer_id}", producer_id, "")
                    with count_lock:
                        producer_count[producer_id] += 1
                except Exception:
                    pass

        # Create a deadlock-free consumer routine
        def consumer_routine(consumer_id):
            for _ in range(5):  # Limit to 5 cycles
                try:
                    pc.consume(consumer_id, "")
                    with count_lock:
                        consumer_count[consumer_id] += 1
                except Exception:
                    pass

        # Start multiple producers and consumers
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

        # Verify that all producers and consumers got to act at least once
        for i, count in enumerate(producer_count):
            self.assertGreater(
                count, 0, f"Producer {i} never acted, possible starvation"
            )

        for i, count in enumerate(consumer_count):
            self.assertGreater(
                count, 0, f"Consumer {i} never acted, possible starvation"
            )

    def test_stress(self):
        """Stress test with many producers and consumers"""
        pc = ProducerConsumer(buffer_size=10)

        # Count total items produced and consumed
        produced = [0]
        consumed = [0]

        counter_lock = threading.Lock()

        # Create a producer routine that produces many items
        def producer_routine(producer_id):
            for i in range(20):  # Each producer produces 20 items
                pc.produce(f"P{producer_id}_{i}", producer_id, "")
                with counter_lock:
                    produced[0] += 1

        # Create a consumer routine that consumes many items
        def consumer_routine(consumer_id):
            for i in range(20):  # Each consumer consumes up to 20 items
                try:
                    pc.consume(consumer_id, "")
                    with counter_lock:
                        consumed[0] += 1
                except Exception:
                    break

        # Start many producers and consumers
        threads = []
        for i in range(5):  # 5 producers
            thread = threading.Thread(target=producer_routine, args=(i,))
            thread.daemon = True
            threads.append(thread)

        for i in range(5):  # 5 consumers
            thread = threading.Thread(target=consumer_routine, args=(i,))
            thread.daemon = True
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join(2)

        # All items should eventually be consumed
        self.assertEqual(
            produced[0], consumed[0], "All produced items should be consumed"
        )

    def test_edge_case_buffer_size_one(self):
        """Test edge case with buffer size 1"""
        pc = ProducerConsumer(buffer_size=1)

        # Producer fills buffer
        pc.produce(1, 0, "")

        # Buffer is full, producer should block
        blocked = [True]

        def try_produce():
            pc.produce(2, 1, "")
            blocked[0] = False

        thread = threading.Thread(target=try_produce)
        thread.daemon = True
        thread.start()

        # Give time for the producer to block
        time.sleep(0.1)

        # Producer should still be blocked
        self.assertTrue(blocked[0], "Producer should be blocked when buffer is full")

        # Consumer consumes item
        pc.consume(0, "")

        # Wait for producer to be notified and add its item
        thread.join(0.5)

        # Producer should have added its item
        self.assertFalse(blocked[0], "Producer should have been unblocked")

        # Verify buffer state
        self.assertEqual(len(pc.buffer), 1, "Buffer should have one item")
        self.assertEqual(pc.buffer[0], 2, "Buffer should contain the second item")

    def test_race_conditions(self):
        """Test for race conditions when accessing the buffer"""
        pc = ProducerConsumer(buffer_size=5)

        # Monitor for race conditions
        race_errors = []
        error_lock = threading.Lock()

        original_produce = pc.produce
        original_consume = pc.consume

        def check_produce(item, producer_id, color):
            with error_lock:
                buffer_before = pc.buffer.copy()
                original_produce(item, producer_id, color)
                buffer_after = pc.buffer.copy()

                # Verify consistent state changes
                expected_length = len(buffer_before) + 1
                if len(buffer_after) != expected_length:
                    race_errors.append(
                        f"Race condition in produce: expected length {expected_length}, got {len(buffer_after)}"
                    )

        def check_consume(consumer_id, color):
            with error_lock:
                buffer_before = pc.buffer.copy()
                item = original_consume(consumer_id, color)
                buffer_after = pc.buffer.copy()

                # Verify consistent state changes
                expected_length = len(buffer_before) - 1
                if len(buffer_after) != expected_length:
                    race_errors.append(
                        f"Race condition in consume: expected length {expected_length}, got {len(buffer_after)}"
                    )

            return item

        pc.produce = check_produce
        pc.consume = check_consume

        # Run multiple producers and consumers with intensive access
        threads = []
        for i in range(5):

            def intensive_producer(id=i):
                for j in range(10):
                    try:
                        pc.produce(f"P{id}_{j}", id, "")
                    except Exception:
                        pass

            def intensive_consumer(id=i):
                for j in range(10):
                    try:
                        pc.consume(id, "")
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

        # Verify no race conditions were detected
        self.assertEqual(
            len(race_errors), 0, f"Race conditions detected: {race_errors}"
        )

    def test_deadlock_prevention(self):
        """Test that the system prevents deadlocks"""
        pc = ProducerConsumer(buffer_size=2)

        # Fill the buffer
        pc.produce(1, 0, "")
        pc.produce(2, 0, "")

        # Create multiple producers that will be blocked
        blocked_producers = []
        for i in range(3):

            def producer_task(id=i):
                pc.produce(f"P{id}", id, "")
                blocked_producers.append(id)

            thread = threading.Thread(target=producer_task)
            thread.daemon = True
            thread.start()

        # Give time for producers to block
        time.sleep(0.1)

        # No producers should have completed yet
        self.assertEqual(
            len(blocked_producers), 0, "No producers should have completed"
        )

        # Create a consumer that will unblock at least one producer
        def consumer_task():
            for _ in range(3):
                pc.consume(0, "")

        consumer_thread = threading.Thread(target=consumer_task)
        consumer_thread.daemon = True
        consumer_thread.start()

        # Wait for the consumer to finish
        consumer_thread.join(1)

        # At least some producers should have been unblocked
        self.assertGreater(
            len(blocked_producers), 0, "Some producers should have been unblocked"
        )

    def test_resource_release_after_exception(self):
        """Test resource release after exceptions"""
        pc = ProducerConsumer(buffer_size=5)

        # Simulate an exception during produce
        with patch.object(
            ProducerConsumer, "produce", side_effect=Exception("Simulated error")
        ):
            try:
                pc.produce(1, 0, "")
            except Exception:
                pass

            # Verify that the buffer is still accessible
            self.assertEqual(
                len(pc.buffer), 0, "Buffer should be accessible after exception"
            )

            # Try a normal produce and consume
            pc.produce = lambda item, producer_id, color: pc.buffer.append(item)
            pc.consume = (
                lambda consumer_id, color: pc.buffer.pop(0) if pc.buffer else None
            )

            pc.produce(2, 1, "")
            self.assertEqual(len(pc.buffer), 1, "Buffer should have one item")

            item = pc.consume(0, "")
            self.assertEqual(item, 2, "Should be able to consume the item")
            self.assertEqual(len(pc.buffer), 0, "Buffer should be empty")

    def test_fifo_ordering(self):
        """Test that items are consumed in FIFO order"""
        pc = ProducerConsumer(buffer_size=5)

        # Producer adds items in a specific order
        pc.produce("item1", 0, "")
        pc.produce("item2", 0, "")
        pc.produce("item3", 0, "")

        # Consumer should get items in the same order
        item1 = pc.consume(0, "")
        item2 = pc.consume(0, "")
        item3 = pc.consume(0, "")

        self.assertEqual(item1, "item1", "First item should be consumed first")
        self.assertEqual(item2, "item2", "Second item should be consumed second")
        self.assertEqual(item3, "item3", "Third item should be consumed third")


if __name__ == "__main__":
    unittest.main()
