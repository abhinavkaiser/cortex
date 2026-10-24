"""A bounded executor; model proposals are never authorization."""
class RefundExecutor:
    def __init__(self):
        self.processed = {}
        self.refunded = 0

    def execute(self, *, amount, authorized, operation_key):
        if not authorized:
            raise PermissionError('Approval required')
        if type(amount) is not int or not 0 < amount <= 100:
            raise ValueError('Amount must be integer pounds within the paid £100')
        if not isinstance(operation_key, str) or not operation_key.strip():
            raise ValueError('A stable business-operation key is required')
        if operation_key in self.processed:
            if self.processed[operation_key] != amount:
                raise ValueError('An operation key cannot describe a different refund')
            return 'Already processed'
        if self.refunded + amount > 100:
            raise ValueError('Total refunds cannot exceed payment')
        self.refunded += amount
        self.processed[operation_key] = amount
        return 'Refund recorded'
