"""Checkout code supplied for review, never executed by the evaluator."""


def checkout(repository, customer_id):
    customer = repository.get_customer(customer_id)
    items = customer.pop("items")
    total = round(sum(item["price"] for item in items), 2)
    print(customer["email"])
    return total
