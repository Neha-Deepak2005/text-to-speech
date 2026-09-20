"""
Shared Flask extension instances.

Kept in their own module (rather than created inside app.py) so route
modules can import `limiter` and attach rate limits without causing a
circular import with the application factory.
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
