"""Business logic that is too rich to live on a model.

Modules here never import the application factory. They take plain arguments or
ORM instances, which keeps them unit-testable without a request context.
"""
