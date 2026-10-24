import unittest
from classifier import confusion
from retrieval import retrieve
from tools import RefundExecutor


class LabTests(unittest.TestCase):
    def test_obsolete_documents_excluded(self):
        docs = [dict(id='old', text='refund policy', current=False), dict(id='new', text='refund policy', current=True)]
        self.assertEqual(retrieve('refund', docs), ['new'])

    def test_confusion_counts(self):
        self.assertEqual(confusion([(10, 0), (80, 1), (90, 0), (20, 1)], 50), dict(tp=1, fp=1, fn=1, tn=1))

    def test_refund_requires_authorization(self):
        with self.assertRaises(PermissionError):
            RefundExecutor().execute(amount=50, authorized=False, operation_key='order-a-refund-1')

    def test_retry_does_not_repeat_refund(self):
        executor = RefundExecutor()
        executor.execute(amount=50, authorized=True, operation_key='order-a-refund-1')
        self.assertEqual(executor.execute(amount=50, authorized=True, operation_key='order-a-refund-1'), 'Already processed')
        self.assertEqual(executor.refunded, 50)

    def test_same_key_cannot_change_amount(self):
        executor = RefundExecutor()
        executor.execute(amount=50, authorized=True, operation_key='refund-1')
        with self.assertRaises(ValueError):
            executor.execute(amount=60, authorized=True, operation_key='refund-1')

    def test_total_cannot_exceed_payment(self):
        executor = RefundExecutor()
        executor.execute(amount=80, authorized=True, operation_key='refund-1')
        with self.assertRaises(ValueError):
            executor.execute(amount=30, authorized=True, operation_key='refund-2')


if __name__ == '__main__':
    unittest.main()
