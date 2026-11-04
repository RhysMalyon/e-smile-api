class CustomerNotFoundError(Exception):
    status_code = 404

    def __init__(self, message: str = "Customer not found."):
        super().__init__(message)


class CustomerAlreadyExistsError(Exception):
    status_code = 409

    def __init__(self, message: str = "A customer with that email already exists."):
        super().__init__(message)
